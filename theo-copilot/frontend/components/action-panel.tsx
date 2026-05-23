'use client';

import { useEffect, useState } from 'react';
import { api, type SuggestedAction, type TicketDetail, type TraceEvent } from '@/lib/api';
import { ChevronDown, ChevronUp, CheckCircle2 } from 'lucide-react';

const LABELS: Record<string, [string, string]> = {
  send_whatsapp_reply:         ['WhatsApp-Antwort senden', '💬'],
  send_email_reply:            ['E-Mail-Antwort senden', '✉'],
  dispatch_vendor:             ['Handwerker beauftragen', '🔧'],
  approve_offer:               ['Angebot freigeben', '✓'],
  request_invoice_itemization: ['Belegaufstellung anfordern', '📑'],
  escalate_to_human:           ['An Team Lead eskalieren', '⬆'],
};

export function ActionPanel({
  ticket, onAfter,
}: { ticket: TicketDetail; onAfter: () => Promise<void> | void }) {
  const actions = ticket.suggested_actions || [];
  if (actions.length === 0) return null;

  const mode = ticket.enrichment?.autonomy_mode || 'propose';
  const rationale = ticket.enrichment?.autonomy_rationale || '';

  if (mode === 'autonomous_done') {
    return <AutonomousDone ticket={ticket} actions={actions} rationale={rationale} />;
  }
  if (mode === 'bundle_approve') {
    return <BundleApprove ticket={ticket} actions={actions} rationale={rationale} onAfter={onAfter} />;
  }
  return <Propose ticket={ticket} actions={actions} onAfter={onAfter} />;
}

// ---------------------------------------------------------------------------
// autonomous_done
// ---------------------------------------------------------------------------

function AutonomousDone({
  ticket, actions, rationale,
}: { ticket: TicketDetail; actions: SuggestedAction[]; rationale: string }) {
  const [showTrace, setShowTrace] = useState(false);
  const [trace, setTrace] = useState<TraceEvent[] | null>(null);

  useEffect(() => {
    if (showTrace && trace === null) {
      api.getTrace(ticket.id).then(setTrace).catch(() => setTrace([]));
    }
  }, [showTrace, ticket.id, trace]);

  return (
    <section className="mt-2">
      <div className="rounded-md border-l-4 border-teal-600 bg-teal-50 px-5 py-4 mb-4">
        <p className="font-semibold text-sm text-teal-800 mb-1 flex items-center gap-2">
          <CheckCircle2 size={16} /> Autonom erledigt
        </p>
        <p className="text-sm text-paper-700">{rationale || 'Theo hat dieses Ticket eigenständig bearbeitet.'}</p>
      </div>

      <h3 className="text-xs font-semibold uppercase tracking-wider text-paper-500 mb-3">
        Durchgeführte Aktionen
      </h3>
      <div className="space-y-3">
        {actions.map((a, i) => {
          const [label, icon] = LABELS[a.action_type] || [a.action_type, '·'];
          const when = a.executed_at ? a.executed_at.slice(11, 16) : '';
          return (
            <div key={i} className="rounded-lg border border-paper-200 bg-white px-5 py-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-md font-semibold text-paper-900">{icon} &nbsp; {label}</p>
                <span className="inline-flex rounded-full border border-green-100 bg-green-50 px-2 py-0.5 text-[11px] font-semibold uppercase text-green-700">
                  ✓ Erledigt {when}
                </span>
              </div>
              <p className="text-sm text-paper-700 leading-snug">{a.rationale}</p>
            </div>
          );
        })}
      </div>

      <button
        onClick={() => setShowTrace((v) => !v)}
        className="mt-4 flex items-center gap-2 text-sm font-medium text-paper-600 hover:text-paper-900"
      >
        {showTrace ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        Was Theo gemacht hat ({trace ? trace.length : '…'} Schritte)
      </button>
      {showTrace && trace && (
        <div className="mt-3 rounded-lg border border-paper-200 bg-white p-3 max-h-80 overflow-y-auto">
          {trace.map((e, i) => (
            <div key={i} className="font-mono text-xs py-1.5 border-b border-paper-100 last:border-b-0">
              <span className="text-paper-500">{e.created_at?.slice(11, 19)}</span>{' '}
              <strong className="text-teal-700">{e.kind}</strong>{' '}
              <span className="text-paper-700">{JSON.stringify(e.payload).slice(0, 160)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// bundle_approve
// ---------------------------------------------------------------------------

function BundleApprove({
  ticket, actions, rationale, onAfter,
}: { ticket: TicketDetail; actions: SuggestedAction[]; rationale: string; onAfter: () => any }) {
  const ordered = [...actions].sort((a, b) => (a.bundle_order ?? 0) - (b.bundle_order ?? 0));
  const waAction = ordered.find((a) => a.action_type === 'send_whatsapp_reply');
  const [draft, setDraft] = useState(waAction?.payload?.body || '');
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; warnings?: string[]; error?: string } | null>(null);

  const run = async () => {
    setPending(true);
    try {
      const res = await api.executeBundle(ticket.id, waAction ? draft : undefined);
      setResult(res);
      await onAfter();
    } catch (e: any) {
      setResult({ ok: false, error: e.message });
    } finally {
      setPending(false);
    }
  };

  return (
    <section className="mt-2">
      <div className="rounded-md border-l-4 border-amber-500 bg-amber-50 px-5 py-4 mb-4">
        <p className="font-semibold text-sm text-amber-700 mb-1">
          Einmal bestätigen — {actions.length} Aktionen
        </p>
        <p className="text-sm text-paper-700">{rationale}</p>
      </div>

      <div className="space-y-3 mb-4">
        {ordered.map((a, i) => {
          const [label, icon] = LABELS[a.action_type] || [a.action_type, '·'];
          return (
            <div key={i} className="rounded-lg border-l-2 border-amber-500 bg-white border border-paper-200 px-5 py-4">
              <p className="text-md font-semibold text-paper-900 mb-2">
                <span className="font-medium text-paper-500 mr-2">{i + 1}.</span>
                {icon} &nbsp; {label}
              </p>
              <p className="text-sm text-paper-700 leading-snug">{a.rationale}</p>
              {a.action_type === 'send_whatsapp_reply' && (
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  className="mt-3 w-full rounded-md border border-paper-300 bg-white px-3 py-2 text-sm font-sans text-paper-900 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-100"
                  rows={6}
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={run}
          disabled={pending}
          className="rounded-md bg-teal-600 px-5 py-2.5 text-base font-medium text-white shadow-sm hover:bg-teal-700 disabled:opacity-50 transition"
        >
          {pending ? 'Wird ausgeführt…' : 'Bündel umsetzen'}
        </button>
        <button
          disabled={pending}
          className="rounded-md border border-paper-300 bg-white px-5 py-2.5 text-base font-medium text-paper-900 hover:bg-paper-50 transition"
        >
          Ablehnen
        </button>
      </div>

      {result && (
        <div className={`mt-3 rounded-md border-l-4 px-4 py-3 text-sm ${
          result.ok ? 'border-green-500 bg-green-50 text-green-800' : 'border-red-500 bg-red-50 text-red-700'
        }`}>
          {result.ok ? `✓ Bündel ausgeführt.` : `Fehler: ${result.error}`}
          {result.warnings?.map((w, i) => <div key={i} className="text-amber-700">⚠ {w}</div>)}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// propose
// ---------------------------------------------------------------------------

function Propose({
  ticket, actions, onAfter,
}: { ticket: TicketDetail; actions: SuggestedAction[]; onAfter: () => any }) {
  return (
    <section className="mt-2">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-paper-500 mb-3">
        Vorgeschlagene Aktionen
      </h3>
      <div className="space-y-3">
        {actions.map((a, i) => (
          <ProposeAction key={i} ticket={ticket} action={a} index={i} onAfter={onAfter} />
        ))}
      </div>
    </section>
  );
}

function ProposeAction({
  ticket, action, index, onAfter,
}: { ticket: TicketDetail; action: SuggestedAction; index: number; onAfter: () => any }) {
  const [label, icon] = LABELS[action.action_type] || [action.action_type, '·'];
  const [draft, setDraft] = useState(action.payload?.body || '');
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const editable = action.action_type === 'send_whatsapp_reply' || action.action_type === 'send_email_reply';

  const run = async () => {
    setPending(true);
    try {
      await api.executeAction(ticket.id, index, editable ? draft : undefined);
      setDone(true);
      await onAfter();
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="rounded-lg border border-paper-200 bg-white px-5 py-4">
      <p className="text-md font-semibold text-paper-900 mb-2">{icon} &nbsp; {label}</p>
      <p className="text-sm text-paper-700 leading-snug mb-3">{action.rationale}</p>
      {editable && (
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={action.action_type === 'send_email_reply' ? 10 : 6}
          className="w-full rounded-md border border-paper-300 bg-white px-3 py-2 text-sm text-paper-900 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-100 mb-3"
        />
      )}
      <div className="flex items-center gap-2">
        <button
          onClick={run}
          disabled={pending || done}
          className="rounded-md bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-teal-700 disabled:opacity-50 transition"
        >
          {done ? '✓ Ausgeführt' : pending ? 'Wird ausgeführt…' : 'Freigeben'}
        </button>
        <button
          disabled={pending || done}
          className="rounded-md border border-paper-300 bg-white px-4 py-2 text-sm font-medium text-paper-900 hover:bg-paper-50 transition"
        >
          Ablehnen
        </button>
      </div>
    </div>
  );
}
