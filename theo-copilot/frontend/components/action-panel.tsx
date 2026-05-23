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

// Map a trace event to a German sentence. Falls back to "schritt unbekannt"
// if we don't have a translation — those will still show in the raw expander.
function humanizeTrace(e: TraceEvent): string | null {
  const p = e.payload || {};
  switch (e.kind) {
    case 'intent_classification':
      return `Anliegen erkannt als „${p.intent}" (Dringlichkeit: ${p.urgency}, Konfidenz ${Math.round((p.confidence || 0) * 100)}%).`;
    case 'tool_use': {
      const name = p.name || '';
      const args = p.args || {};
      if (name === 'get_tenant' || name === 'get_tenant_by_phone')
        return `Mieter:in nachgeschlagen.`;
      if (name === 'get_unit')
        return `Wohneinheit nachgeschlagen.`;
      if (name === 'get_lease')
        return `Mietvertrag eingesehen.`;
      if (name === 'list_tickets')
        return `Vorgangshistorie geprüft (Einheit ${args.unit_id || '?'}).`;
      if (name === 'get_ticket')
        return `Einzelnen Vorgang vertieft eingesehen.`;
      if (name === 'list_invoices')
        return `Rechnungen geprüft.`;
      if (name === 'get_nka')
        return `Nebenkostenabrechnung eingesehen.`;
      if (name === 'get_open_offers')
        return `Offene Vendor-Angebote geprüft.`;
      if (name === 'get_vendor')
        return `Handwerker-Stammdaten geprüft.`;
      if (name === 'list_internal_chat')
        return `Internen Chat (Sarah ↔ Jonas) eingesehen.`;
      if (name === 'query_temporal_memory')
        return `Temporales Gedächtnis abgefragt: „${args.query || ''}".`;
      if (name === 'get_entity_timeline')
        return `Zeitachse einer Entität abgerufen.`;
      if (name === 'search_wiki')
        return `Wissensbasis durchsucht: „${args.query || ''}".`;
      if (name === 'read_wiki_page')
        return `Wiki-Seite gelesen: ${args.path || '?'}.`;
      if (name === 'get_weather_forecast')
        return `Wettervorhersage abgerufen (${args.location || '?'}).`;
      if (name === 'send_whatsapp_reply')
        return `WhatsApp-Antwort gesendet.`;
      if (name === 'send_email_reply')
        return `E-Mail-Antwort gesendet: „${args.subject || ''}".`;
      if (name === 'dispatch_vendor')
        return `Handwerker beauftragt.`;
      if (name === 'approve_offer')
        return `Angebot freigegeben.`;
      return `Werkzeug aufgerufen: ${name}.`;
    }
    case 'stubbed_tool':
      return `Hinweis: Werkzeug „${p.name}" mit Demodaten beantwortet.`;
    case 'enrichment_payload':
      if (p.autonomy_mode === 'autonomous_done')
        return `Entscheidung: autonom ausführen — alle Sicherheits-Schranken erfüllt.`;
      if (p.autonomy_mode === 'bundle_approve')
        return `Entscheidung: Aktionen-Paket zur Freigabe vorschlagen.`;
      return `Anreicherungs-Paket erstellt.`;
    case 'llm_call_started':
    case 'llm_call_completed':
    case 'tool_result':
      return null;   // background noise; available via raw view
    case 'error':
      return `Fehler aufgetreten — siehe Detailansicht.`;
    default:
      return null;
  }
}

function AutonomousDone({
  ticket, actions, rationale,
}: { ticket: TicketDetail; actions: SuggestedAction[]; rationale: string }) {
  const [showSteps, setShowSteps] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const [trace, setTrace] = useState<TraceEvent[] | null>(null);

  useEffect(() => {
    if ((showSteps || showRaw) && trace === null) {
      api.getTrace(ticket.id).then(setTrace).catch(() => setTrace([]));
    }
  }, [showSteps, showRaw, ticket.id, trace]);

  const humanSteps = trace
    ? trace.map((e) => ({ e, text: humanizeTrace(e) })).filter((x) => x.text !== null)
    : null;

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
        onClick={() => setShowSteps((v) => !v)}
        className="mt-4 flex items-center gap-2 text-sm font-medium text-paper-700 hover:text-paper-900"
      >
        {showSteps ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        Wie Theo vorgegangen ist
      </button>
      {showSteps && humanSteps && (
        <ol className="mt-3 rounded-lg border border-paper-200 bg-white p-4 space-y-2 list-decimal list-inside">
          {humanSteps.map(({ e, text }, i) => (
            <li key={i} className="text-sm text-paper-900 leading-snug">{text}</li>
          ))}
          {humanSteps.length === 0 && (
            <p className="text-sm text-paper-500 italic">Keine Übersicht verfügbar.</p>
          )}
        </ol>
      )}

      {showSteps && (
        <button
          onClick={() => setShowRaw((v) => !v)}
          className="mt-2 flex items-center gap-2 text-xs font-medium text-paper-500 hover:text-paper-700"
        >
          {showRaw ? '▾' : '▸'} Technische Details
        </button>
      )}
      {showRaw && trace && (
        <div className="mt-2 rounded-lg border border-paper-200 bg-paper-50 p-3 max-h-80 overflow-y-auto">
          {trace.map((e, i) => (
            <div key={i} className="font-mono text-xs py-1.5 border-b border-paper-100 last:border-b-0">
              <span className="text-paper-500">{e.created_at?.slice(11, 19)}</span>{' '}
              <strong className="text-teal-700">{e.kind}</strong>{' '}
              <span className="text-paper-700">{JSON.stringify(e.payload).slice(0, 200)}</span>
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
          {pending ? 'Wird ausgeführt…' : 'Aktionen umsetzen'}
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
          {result.ok ? `✓ Aktionen ausgeführt.` : `Fehler: ${result.error}`}
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
