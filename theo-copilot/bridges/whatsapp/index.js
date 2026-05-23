// Theo Copilot — WhatsApp bridge (Baileys → theo-intake)
//
// Inbound:  WhatsApp message → POST {INTAKE_URL}/webhook/whatsapp
// Outbound: POST /send {to: "+49...", body: "..."} → sock.sendMessage
// Health:   GET /health
// QR pairing: scan the QR printed in `journalctl -u theo-whatsapp-bridge -f`
//
// Env:
//   AUTH_DIR                — where Baileys stores creds (default /opt/fletcher/baileys-auth)
//   INTAKE_URL              — Python intake base URL (default http://127.0.0.1:8002)
//   BRIDGE_PORT             — HTTP port to listen on (default 8003)
//   WHATSAPP_ALLOWED_NUMBERS — comma-separated E.164 allowlist for OUTBOUND. Empty = allow all.

import express from 'express';
import pino from 'pino';
import qrcode from 'qrcode-terminal';
import {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
} from '@whiskeysockets/baileys';

const log = pino({ level: process.env.LOG_LEVEL || 'info' });

const AUTH_DIR = process.env.AUTH_DIR || '/opt/fletcher/baileys-auth';
const INTAKE_URL = process.env.INTAKE_URL || 'http://127.0.0.1:8002';
const PORT = parseInt(process.env.BRIDGE_PORT || '8003', 10);
const ALLOWED = (process.env.WHATSAPP_ALLOWED_NUMBERS || '')
  .split(',').map(s => s.trim()).filter(Boolean);

let sock = null;
let bridgeReady = false;
let lastQr = null;
let ownJid = null;     // e.g. "493012345678:64@s.whatsapp.net"
let ownNumber = null;  // e.g. "+493012345678"
let ownPnDigits = null; // "493012345678"
let ownLidDigits = null; // "150010406641734" — LID, different from phone number

function jidToE164(jid) {
  // "493061523 81@s.whatsapp.net" → "+49306152381"
  if (!jid) return null;
  const digits = jid.split('@')[0].replace(/[^\d]/g, '');
  return digits ? `+${digits}` : null;
}

function e164ToJid(phone) {
  // "+49306152381" → "493061523 81@s.whatsapp.net"
  const digits = (phone || '').replace(/[^\d]/g, '');
  return digits ? `${digits}@s.whatsapp.net` : null;
}

function extractText(msgOrWrapper) {
  // Accepts either the full m.message object OR a wrapped inner message
  // (ephemeralMessage / viewOnceMessage / etc). Recursive unwrap.
  let msg = msgOrWrapper;
  if (!msg) return '';
  // Some shapes pass the outer messageInfo as input — unwrap it first.
  if (msg.message) msg = msg.message;
  if (!msg) return '';

  // Wrappers — recurse into .message
  if (msg.ephemeralMessage?.message) return extractText(msg.ephemeralMessage.message);
  if (msg.viewOnceMessage?.message) return extractText(msg.viewOnceMessage.message);
  if (msg.viewOnceMessageV2?.message) return extractText(msg.viewOnceMessageV2.message);
  if (msg.viewOnceMessageV2Extension?.message) return extractText(msg.viewOnceMessageV2Extension.message);
  if (msg.documentWithCaptionMessage?.message) return extractText(msg.documentWithCaptionMessage.message);
  if (msg.editedMessage?.message) return extractText(msg.editedMessage.message);

  // Direct text variants
  if (msg.conversation) return msg.conversation;
  if (msg.extendedTextMessage?.text) return msg.extendedTextMessage.text;
  if (msg.imageMessage?.caption) return msg.imageMessage.caption;
  if (msg.videoMessage?.caption) return msg.videoMessage.caption;
  if (msg.documentMessage?.caption) return msg.documentMessage.caption;
  if (msg.audioMessage?.caption) return msg.audioMessage.caption;
  if (msg.templateButtonReplyMessage?.selectedDisplayText) return msg.templateButtonReplyMessage.selectedDisplayText;
  if (msg.buttonsResponseMessage?.selectedDisplayText) return msg.buttonsResponseMessage.selectedDisplayText;
  if (msg.listResponseMessage?.title) return msg.listResponseMessage.title;
  return '';
}

async function forwardInbound(m, opts = {}) {
  // For self-chat over LID, remoteJid is the LID (not the phone number).
  // Override with our own phone so the intake's tenant-by-phone lookup works.
  const from = opts.selfChat && ownNumber
    ? ownNumber
    : jidToE164(m.key.remoteJid);
  if (!from) return;
  // Skip group chats for the demo
  if (m.key.remoteJid?.endsWith('@g.us')) {
    log.info({ from: m.key.remoteJid }, 'skipping group message');
    return;
  }
  const body = extractText(m);
  if (!body) {
    // Log the message type keys so we can see what we missed
    const keys = m.message ? Object.keys(m.message).slice(0, 8) : [];
    log.info({ from, messageKeys: keys }, 'skipping non-text message');
    return;
  }
  const sentAt = new Date((m.messageTimestamp || Date.now() / 1000) * 1000).toISOString();
  const payload = {
    from,
    body,
    sent_at: sentAt,
    external_thread_id: `wa-${from}`,
    self_chat: !!opts.selfChat,
  };
  try {
    const res = await fetch(`${INTAKE_URL}/webhook/whatsapp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    log.info({ from, status: res.status, selfChat: !!opts.selfChat }, 'forwarded inbound');
  } catch (err) {
    log.error({ err: err.message, from }, 'forward to intake failed');
  }
}

async function startSocket() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();
  log.info({ version }, 'using Baileys WA version');

  sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: 'warn' }),
    printQRInTerminal: false,
    browser: ['Theo Copilot', 'Desktop', '1.0.0'],
    markOnlineOnConnect: false,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      lastQr = qr;
      log.info('--- scan this QR with WhatsApp (Settings → Linked Devices) ---');
      qrcode.generate(qr, { small: true });
    }
    if (connection === 'open') {
      bridgeReady = true;
      lastQr = null;
      ownJid = sock.user?.id || null;
      const lidRaw = sock.user?.lid || null;
      if (ownJid) {
        ownPnDigits = ownJid.split(':')[0].split('@')[0].replace(/[^\d]/g, '');
        ownNumber = ownPnDigits ? `+${ownPnDigits}` : null;
      }
      if (lidRaw) {
        ownLidDigits = lidRaw.split(':')[0].split('@')[0].replace(/[^\d]/g, '');
      }
      log.info({ ownNumber, ownJid, lidRaw, ownLidDigits }, 'WhatsApp connection OPEN');
    }
    if (connection === 'close') {
      bridgeReady = false;
      const code = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = code !== DisconnectReason.loggedOut;
      log.warn({ code, shouldReconnect }, 'connection closed');
      if (shouldReconnect) {
        setTimeout(() => startSocket().catch(err => log.error(err)), 3000);
      } else {
        log.error('logged out — clear auth dir and restart to re-pair');
      }
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const m of messages) {
      const remoteDigits = (m.key.remoteJid || '').split('@')[0].replace(/[^\d]/g, '');
      const isLid = (m.key.remoteJid || '').endsWith('@lid');
      // Self-chat detection: remote matches our PN OR our LID
      const isSelfChat = m.key.fromMe && (
        (ownPnDigits && remoteDigits === ownPnDigits) ||
        (ownLidDigits && remoteDigits === ownLidDigits)
      );
      log.info({
        remoteJid: m.key.remoteJid, fromMe: m.key.fromMe,
        isLid, isSelfChat, remoteDigits,
      }, 'incoming message');
      if (m.key.fromMe && !isSelfChat) continue;
      forwardInbound(m, { selfChat: isSelfChat }).catch(err => log.error({ err: err.message }, 'forward error'));
    }
  });
}

// --- HTTP control plane ---

const app = express();
app.use(express.json({ limit: '1mb' }));

app.get('/health', (req, res) => {
  res.json({
    status: bridgeReady ? 'ready' : 'pairing',
    paired: bridgeReady,
    qr_pending: !!lastQr,
    own_number: ownNumber,
  });
});

app.get('/me', (req, res) => {
  res.json({ own_number: ownNumber, paired: bridgeReady });
});

app.get('/qr', (req, res) => {
  // Returns the QR string so a client can render it; empty when paired
  res.json({ qr: lastQr, paired: bridgeReady });
});

app.post('/send', async (req, res) => {
  const { to, body } = req.body || {};
  if (!to || !body) return res.status(400).json({ error: 'to and body required' });
  if (!bridgeReady || !sock) {
    return res.status(503).json({ error: 'bridge not ready / not paired' });
  }
  // Outbound allowlist
  if (ALLOWED.length > 0) {
    const normTo = to.replace(/[^\d+]/g, '');
    if (!ALLOWED.some(a => a.replace(/[^\d+]/g, '') === normTo)) {
      log.warn({ to }, 'outbound rejected — not in allowlist');
      return res.status(403).json({ error: 'recipient not in WHATSAPP_ALLOWED_NUMBERS' });
    }
  }
  try {
    const jid = e164ToJid(to);
    const result = await sock.sendMessage(jid, { text: body });
    log.info({ to, msgId: result?.key?.id }, 'sent');
    res.json({ ok: true, message_id: result?.key?.id });
  } catch (err) {
    log.error({ err: err.message, to }, 'send failed');
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, '127.0.0.1', () => {
  log.info({ port: PORT, allowlist: ALLOWED.length || 'OPEN' }, 'bridge HTTP control plane up');
});

// Kick off the WhatsApp socket
startSocket().catch(err => {
  log.error({ err: err.message }, 'startup failed');
  process.exit(1);
});
