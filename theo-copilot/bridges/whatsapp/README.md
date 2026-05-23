# Theo WhatsApp Bridge (Baileys)

Connects the Theo Copilot intake to a real WhatsApp account using the
unofficial multi-device protocol (`@whiskeysockets/baileys`).

> ⚠️ Unofficial. WhatsApp can ban an account they detect as automated.
> Use a throwaway number, not your personal one. Risk is low for hackathon
> traffic but non-zero.

## Architecture

```
WhatsApp ←→ Baileys (Node, :8003) ←→ HTTP ←→ theo-intake (:8002)
                ↓
        /opt/fletcher/baileys-auth/   (creds + keys persisted)
```

- **Inbound** WhatsApp message → bridge → `POST /webhook/whatsapp` on the
  Python intake → ticket creation + enrichment.
- **Outbound** (after Sarah approves a draft in the Streamlit UI) →
  Python `execute_send_whatsapp` → `POST http://127.0.0.1:8003/send` →
  Baileys → WhatsApp.

## Pairing (one-time)

1. Make sure the `theo-whatsapp-bridge` systemd unit is running on the server:
   ```bash
   systemctl status theo-whatsapp-bridge
   ```
2. Stream the logs to see the QR code:
   ```bash
   journalctl -u theo-whatsapp-bridge -f
   ```
3. On a phone with WhatsApp: **Settings → Linked Devices → Link a Device**.
   Scan the QR shown in the terminal.
4. The log will print `WhatsApp connection OPEN` — pairing complete. Creds
   are saved to `/opt/fletcher/baileys-auth/` and persist across restarts.

## Demo wiring

For the Köhler workflow to work end-to-end:

1. **Pick which phone plays "Sarah" (the linked Baileys account)** — call it
   `+49NNN_SARAH`. This is the number tenants see when Theo sends replies.
2. **Pick which phone plays "Frau Köhler"** — call it `+49NNN_KOEHLER`. This
   is the phone that sends the demo message.
3. Update the seeded tenant phone to match the Köhler test phone:
   ```bash
   docker exec fletcher-db psql -U fletcher -d fletcher -c \
     "UPDATE theo.tenants SET phone='+49NNN_KOEHLER' WHERE id='koehler';"
   ```
4. Lock outbound so the agent can only message the Köhler test phone:
   ```
   # in /opt/fletcher/.env
   WHATSAPP_ALLOWED_NUMBERS=+49NNN_KOEHLER
   ```
   Then `systemctl restart theo-whatsapp-bridge`.
5. From the Köhler test phone, send the demo message to `+49NNN_SARAH`.
   The ticket appears in https://getfletcher.ai/inbox within ~3s.

## Env vars

| Var | Default | Notes |
|---|---|---|
| `AUTH_DIR` | `/opt/fletcher/baileys-auth` | persistent creds |
| `INTAKE_URL` | `http://127.0.0.1:8002` | where to POST inbound |
| `BRIDGE_PORT` | `8003` | HTTP control plane |
| `WHATSAPP_ALLOWED_NUMBERS` | `` | comma-separated E.164 allowlist. Empty = OPEN (dangerous). |
| `LOG_LEVEL` | `info` | pino log level |

## HTTP control plane

- `GET /health` — bridge state (`ready` / `pairing`)
- `GET /qr` — current QR string if not paired
- `POST /send` `{to, body}` — send outbound (allowlist enforced)

## Safety rules

- Group chats are ignored on inbound (no `@g.us` JIDs forwarded).
- Non-text messages skipped on inbound.
- Outbound rejected when recipient not in `WHATSAPP_ALLOWED_NUMBERS`.
- Bridge does NOT auto-create tenants for unknown senders — the Python
  intake rejects unknown phones with `status=rejected`.
