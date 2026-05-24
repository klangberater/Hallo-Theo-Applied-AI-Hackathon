'use client';

import { useEffect, useState } from 'react';
import { api, type ThreadMessage, type TicketDetail } from '@/lib/api';
import { ActionPanel } from '@/components/action-panel';
import { CheckCircle2, RotateCcw } from 'lucide-react';

const DONE_GRACE_HOURS = 72;

function fmt(iso: string): string {
  return new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  });
}

function ago(iso: string | null): string {
  if (!iso) return '';
  const sec = (Date.now() - new Date(iso).getTime()) / 1000;
  if (sec < 60) return 'gerade eben';
  if (sec < 3600) return `vor ${Math.floor(sec / 60)} Min.`;
  if (sec < 86400) return `vor ${Math.floor(sec / 3600)} Std.`;
  return `vor ${Math.floor(sec / 86400)} Tagen`;
}

function archiveRemaining(done_at: string | null): string {
  if (!done_at) return 'in Kürze';
  const archiveAt = new Date(done_at).getTime() + DONE_GRACE_HOURS * 3600 * 1000;
  const sec = (archiveAt - Date.now()) / 1000;
  if (sec <= 0) return 'in Kürze';
  const days = Math.floor(sec / 86400);
  const hours = Math.floor((sec % 86400) / 3600);
  if (days) return `in ${days}T ${hours}h`;
  const mins = Math.floor((sec % 3600) / 60);
  return `in ${hours}h ${mins}Min.`;
}

function shortDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.${d.getFullYear()}`;
}

function PriorityChip({ priority }: { priority: string | null }) {
  if (priority === 'DRINGEND')
    return <span className="inline-flex whitespace-nowrap rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[11px] font-semibold uppercase text-red-700">Dringend</span>;
  if (priority === 'Hoch' || priority === 'Wichtig')
    return <span className="inline-flex whitespace-nowrap rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold uppercase text-amber-700">Wichtig</span>;
  return <span className="inline-flex whitespace-nowrap rounded-full border border-paper-200 bg-paper-100 px-2 py-0.5 text-[11px] font-semibold uppercase text-paper-700">Standard</span>;
}

function MarkDoneDialog({
  ticket, open, onClose, onConfirmed,
}: {
  ticket: TicketDetail;
  open: boolean;
  onClose: () => void;
  onConfirmed: () => Promise<void> | void;
}) {
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  // Reset when dialog opens
  useEffect(() => {
    if (open) { setNote(''); setBusy(false); }
  }, [open]);

  if (!open) return null;

  const submit = async () => {
    setBusy(true);
    try {
      await api.markDone(ticket.id, note.trim() || undefined);
      await onConfirmed();
      onClose();
    } catch (e: any) {
      console.error(e);
      alert(`Fehler: ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-paper-900/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-serif text-xl font-medium mb-3 text-paper-900">
          Ticket als erledigt markieren?
        </h3>
        <p className="text-sm text-paper-700 mb-4 leading-relaxed">
          Dies schließt die Konversation mit{' '}
          <strong>{ticket.tenant_name}</strong>. Das Ticket bleibt 3 Tage im
          Posteingang, dann wandert es ins Archiv. Sie können dies jederzeit
          rückgängig machen.
        </p>
        <label className="block text-xs font-semibold uppercase tracking-wide text-paper-500 mb-1">
          Lösungsnotiz (optional)
        </label>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={280}
          autoFocus
          placeholder="z.B. Heizkörper von Bergmann zurückgesetzt, Mieterin bestätigt."
          className="w-full rounded-md border border-paper-300 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-100"
        />
        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={busy}
            className="rounded-md border border-paper-300 bg-white px-4 py-2 text-sm font-medium text-paper-900 hover:bg-paper-50 transition disabled:opacity-50"
          >
            Abbrechen
          </button>
          <button
            onClick={submit}
            disabled={busy}
            className="rounded-md border border-teal-600 bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700 transition disabled:opacity-50"
          >
            {busy ? 'Wird gespeichert…' : 'Erledigt'}
          </button>
        </div>
      </div>
    </div>
  );
}

function DoneBanner({
  ticket, onReopened,
}: {
  ticket: TicketDetail;
  onReopened: (ticketId: string) => Promise<void> | void;
}) {
  // Hooks must run unconditionally — declare them before any early return.
  const [busy, setBusy] = useState(false);
  const state = ticket.derived_state;
  if (state !== 'done' && state !== 'archived') return null;

  const reopen = async () => {
    setBusy(true);
    try {
      await api.reopen(ticket.id);
      await onReopened(ticket.id);
    } catch (e: any) {
      console.error(e);
      alert(`Fehler: ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  const note = (ticket.resolution_note || '').trim();
  const text =
    state === 'done'
      ? `Erledigt ${ago(ticket.done_at)} von ${ticket.done_by || '—'}. Automatische Archivierung ${archiveRemaining(ticket.done_at)}.`
      : `Archiviert. Erledigt am ${shortDate(ticket.done_at)}${ticket.done_by ? ' von ' + ticket.done_by : ''}.`;

  const containerCls =
    state === 'done'
      ? 'rounded-md border-l-[3px] border-green-600 bg-green-50 px-5 py-4 mb-5'
      : 'rounded-md border-l-[3px] border-paper-400 bg-paper-100 px-5 py-4 mb-5';
  const textCls =
    state === 'done'
      ? 'text-sm font-semibold text-green-700 leading-snug'
      : 'text-sm font-semibold text-paper-700 leading-snug';

  return (
    <div className={containerCls}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className={textCls}>{text}</p>
          {note && (
            <p className="text-sm text-paper-700 mt-2 italic">Notiz: {note}</p>
          )}
        </div>
        <button
          onClick={reopen}
          disabled={busy}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-md border border-paper-300 bg-white px-3 py-1.5 text-sm font-medium text-paper-900 hover:bg-paper-50 transition disabled:opacity-50"
        >
          <RotateCcw size={14} /> {busy ? 'Wird wiedereröffnet…' : 'Wiedereröffnen'}
        </button>
      </div>
    </div>
  );
}

export function TicketView({
  ticket, onAfter, onReopened,
}: {
  ticket: TicketDetail;
  onAfter: () => Promise<void> | void;
  onReopened?: (ticketId: string) => Promise<void> | void;
}) {
  const [messages, setMessages] = useState<ThreadMessage[]>([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  // Fall back to onAfter (ignoring the ticket id) if the parent didn't
  // wire a dedicated reopen callback.
  const handleReopen = onReopened ?? (async () => { await onAfter(); });

  useEffect(() => {
    // Clear stale messages from the previously-selected ticket so we never
    // show "wrong conversation under right header" during the ~200ms fetch
    // window. The render falls back to ticket.full_text while messages is
    // empty, which at least matches the ticket actually being shown.
    setMessages([]);
    api.getThread(ticket.id).then(setMessages).catch(() => setMessages([]));
  }, [ticket.id]);

  const state = ticket.derived_state;
  const canMarkDone = state === 'open';
  const isArchived = state === 'archived';

  return (
    <div className="px-8 py-6">
      {/* Header */}
      <header className="border-b border-paper-200 pb-4 mb-6">
        <div className="flex items-start justify-between gap-4 mb-2">
          <h2 className="font-serif text-2xl font-medium leading-tight tracking-tight text-paper-900">
            {ticket.tenant_name} — {ticket.unit_label}
          </h2>
          {canMarkDone && (
            <button
              onClick={() => setConfirmOpen(true)}
              className="shrink-0 inline-flex items-center gap-1.5 rounded-md border border-paper-300 bg-white px-3 py-1.5 text-sm font-medium text-paper-900 hover:bg-paper-50 transition"
            >
              <CheckCircle2 size={14} /> Als erledigt markieren
            </button>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-paper-500">
          <span>{ticket.property_address}</span>
          <span className="text-paper-400">·</span>
          <span>Ticket <code className="font-mono text-xs">{ticket.id}</code></span>
          <span className="text-paper-400">·</span>
          <PriorityChip priority={ticket.priority} />
          <span className="inline-flex rounded-full border border-blue-100 bg-blue-50 px-2 py-0.5 text-[11px] font-semibold uppercase text-blue-600">
            {(ticket.status || '').replace(/_/g, ' ')}
          </span>
        </div>
      </header>

      {/* Done / Archived banner */}
      <DoneBanner ticket={ticket} onReopened={handleReopen} />

      {/* Conversation */}
      <section className="mb-6">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-paper-500 mb-3">
          Konversation
        </h3>
        {messages.length === 0 ? (
          <div className="rounded-lg bg-paper-100 px-5 py-4">
            <div className="text-xs text-paper-500 mb-1">
              <strong className="font-semibold text-paper-900">{ticket.tenant_name}</strong>
            </div>
            <p className="whitespace-pre-wrap text-paper-900">{ticket.full_text}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((m) => (
              <div
                key={m.id}
                className={m.direction === 'outbound'
                  ? 'rounded-lg border-l-2 border-teal-600 bg-teal-50 px-5 py-4'
                  : 'rounded-lg bg-paper-100 px-5 py-4'}
              >
                <div className="text-xs text-paper-500 mb-1 flex gap-2">
                  <strong className="font-semibold text-paper-900">{m.sender}</strong>
                  <span>·</span>
                  <span>{fmt(m.sent_at)}</span>
                </div>
                <p className="whitespace-pre-wrap text-paper-900 leading-relaxed">{m.body}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Action panel — hidden in archived view per spec §8.3 */}
      {!isArchived && <ActionPanel ticket={ticket} onAfter={onAfter} />}

      {/* Mark-as-done confirmation dialog */}
      <MarkDoneDialog
        ticket={ticket}
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirmed={onAfter}
      />
    </div>
  );
}
