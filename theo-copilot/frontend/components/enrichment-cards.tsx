'use client';

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import type { TicketDetail } from '@/lib/api';

function Card({ title, source, children }: {
  title: string; source?: string | null; children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-paper-200 bg-white px-5 py-4 mb-3">
      <div className="text-xs font-semibold uppercase tracking-wider text-paper-500 mb-3 flex items-center gap-2">
        <span>{title}</span>
        {source && <SourcePill source={source} />}
      </div>
      {children}
    </div>
  );
}

function SourcePill({ source }: { source: string }) {
  const styles: Record<string, string> = {
    graphiti: 'bg-teal-50 text-teal-800 border-teal-200',
    'postgres-fallback': 'bg-blue-50 text-blue-600 border-blue-100',
    stub: 'bg-amber-50 text-amber-700 border-amber-200',
    cache: 'bg-paper-100 text-paper-700 border-paper-200',
  };
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${styles[source] || styles.cache}`}>
      {source.replace('-', ' ')}
    </span>
  );
}

function Citations({ sources }: { sources?: any[] }) {
  if (!sources?.length) return null;
  return (
    <div className="mt-3 text-xs font-mono text-paper-500">
      📎 {sources.map((s) => s?.id || s?.kind || 'src').join(' · ')}
    </div>
  );
}

function PatternTimeline({ entries }: { entries: any[] }) {
  if (!entries?.length) return null;
  const sorted = [...entries].sort((a, b) => (a.date || '').localeCompare(b.date || ''));
  const today = new Date();
  return (
    <div className="border-l-2 border-paper-200 pl-3">
      {sorted.map((entry, i) => {
        const d = entry.date ? new Date(entry.date) : null;
        const ago = d ? Math.floor((today.getTime() - d.getTime()) / 86400000) : 0;
        const color = ago < 90 ? 'bg-red-500' : ago < 365 ? 'bg-amber-500' : 'bg-paper-400';
        const when = d ? d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '?';
        const src = typeof entry.source === 'object' ? entry.source?.id : entry.source;
        return (
          <div key={i} className="flex items-start gap-3 mb-3">
            <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${color}`} />
            <div className="min-w-[5.5rem] shrink-0 text-xs text-paper-500 tabular-nums pt-0.5">{when}</div>
            <div className="flex-1 text-sm text-paper-900">
              {entry.fact}
              {src && <div className="text-xs font-mono text-paper-500">📎 {src}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Hints rotated through during the ~30–80s enrichment window. Each one
// reflects something the agent actually does — L1 wiki search, L2 Postgres
// lookup, L3 Graphiti temporal query — so the operator can see roughly
// what's happening even though we don't stream real trace events yet.
const ENRICHING_HINTS = [
  'Mieterhistorie wird geladen…',
  'Vergangene Vorfälle werden gesucht…',
  'Mietvertrag wird ausgelesen…',
  'Wiki wird durchsucht (BGB, BetrKV, interne Richtlinien)…',
  'Vendor-Angebote werden geprüft…',
  'Wetterprognose wird abgerufen…',
  'Vorschläge werden formuliert…',
];

function SkeletonCard({ heightClass = 'h-16' }: { heightClass?: string }) {
  return (
    <div className="rounded-md border border-paper-200 bg-white px-5 py-4 mb-3">
      <div className="h-3 w-32 rounded bg-paper-200 mb-3 animate-pulse" />
      <div className={`${heightClass} rounded bg-paper-100 animate-pulse`} />
    </div>
  );
}

function EnrichingState({ ticket }: { ticket: TicketDetail }) {
  const [hintIdx, setHintIdx] = useState(0);
  useEffect(() => {
    const id = setInterval(() => {
      setHintIdx((i) => (i + 1) % ENRICHING_HINTS.length);
    }, 2500);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <div className="rounded-md border border-teal-200 bg-teal-50 px-5 py-4 mb-3">
        <div className="flex items-center gap-3">
          <Loader2 size={18} className="animate-spin text-teal-700 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-teal-900">
              Fletcher Copilot reichert das Ticket an
            </p>
            <p className="text-xs text-teal-700 mt-0.5 transition-opacity">
              {ENRICHING_HINTS[hintIdx]}
            </p>
          </div>
        </div>
        <p className="mt-3 text-xs text-teal-700/70">
          Dauert typischerweise 30–80 Sekunden. Die Anreicherung erscheint
          automatisch, sobald sie fertig ist.
        </p>
      </div>

      {/* Skeleton placeholders that roughly match the real card layout, so
          the right pane doesn't jump when the real data arrives. */}
      <SkeletonCard heightClass="h-12" />
      <SkeletonCard heightClass="h-20" />
      <SkeletonCard heightClass="h-32" />
      <SkeletonCard heightClass="h-16" />
    </div>
  );
}

export function EnrichmentCards({ ticket }: { ticket: TicketDetail }) {
  const e = ticket.enrichment;
  if (!e) {
    // Show the rich enriching state for any ticket that's still being
    // processed (open OR enriching). Only fall back to "Keine Anreicherung"
    // for clearly-finished tickets that simply have no enrichment payload.
    const isInFlight = ticket.status === 'open' || ticket.status === 'enriching';
    if (isInFlight) return <EnrichingState ticket={ticket} />;
    return (
      <div className="rounded-md border border-paper-200 bg-white px-5 py-4 text-sm text-paper-500">
        Keine Anreicherungsdaten.
      </div>
    );
  }

  return (
    <div>
      {/* Tenant */}
      {e.tenant_card && (
        <Card title="Mieter:in">
          <p className="text-md font-semibold mb-1">{e.tenant_card.name}</p>
          {e.tenant_card.since && <p className="text-sm text-paper-700 mb-3">Mietverhältnis seit {e.tenant_card.since}</p>}
          {e.tenant_card.warnings?.length > 0 && (
            <ul className="space-y-2">
              {e.tenant_card.warnings.map((w: string, i: number) => (
                <li key={i} className="relative pl-5 text-sm text-paper-900 font-medium">
                  <span className="absolute left-0 top-2 h-1.5 w-1.5 rounded-full bg-red-500" />
                  {w}
                </li>
              ))}
            </ul>
          )}
          <Citations sources={e.tenant_card.sources} />
        </Card>
      )}

      {/* Unit */}
      {e.unit_card && (
        <Card title="Wohneinheit">
          <p className="text-md font-semibold mb-1">{e.unit_card.label}</p>
          <p className="text-sm text-paper-700">
            {[e.unit_card.qm && `${e.unit_card.qm} qm`,
              e.unit_card.rent_cold && `${e.unit_card.rent_cold} € kalt`,
              e.unit_card.lease_status].filter(Boolean).join(' · ')}
          </p>
          <Citations sources={e.unit_card.sources} />
        </Card>
      )}

      {/* Lease facts */}
      {e.lease_facts?.length > 0 && (
        <Card title="Mietvertrag-Auszüge">
          <ul className="space-y-2">
            {e.lease_facts.map((f: string, i: number) => (
              <li key={i} className="relative pl-5 text-sm text-paper-700">
                <span className="absolute left-0 top-2 h-1.5 w-1.5 rounded-full bg-paper-400" />
                {f}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Pattern */}
      {e.prior_incidents && (
        <Card title={`Pattern — ${e.prior_incidents.count} Vorfälle in ${e.prior_incidents.timespan_months || '?'} Monaten`} source={e.prior_incidents.source}>
          {e.prior_incidents.pattern_summary && (
            <p className="text-sm italic text-paper-700 mb-4">{e.prior_incidents.pattern_summary}</p>
          )}
          <PatternTimeline entries={e.prior_incidents.timeline || []} />
        </Card>
      )}

      {/* Open offers */}
      {e.open_vendor_offers?.length > 0 && (
        <Card title="Offene Angebote">
          {e.open_vendor_offers.map((o: any, i: number) => (
            <div key={i} className="mb-3 last:mb-0">
              <p className="text-md font-semibold">{o.vendor_name || o.vendor_id} — {o.amount?.toFixed?.(2) || o.amount} €</p>
              <p className="text-sm text-paper-700 mb-1">{o.scope}</p>
              {o.age_days && (
                <p className="text-sm text-red-600 font-medium">⚠ Seit {o.age_days} Tagen unbearbeitet</p>
              )}
            </div>
          ))}
        </Card>
      )}

      {/* Internal pre-approvals (Jonas) */}
      {e.internal_pre_approvals?.length > 0 && (
        <Card title="Interne Vorab-Genehmigung" source="graphiti">
          {e.internal_pre_approvals.map((p: any, i: number) => (
            <div key={i} className="mb-3 last:mb-0">
              <p className="text-sm font-semibold mb-1">
                {p.sender} <span className="text-paper-500 font-normal">· {p.sent_at}</span>
              </p>
              <blockquote className="border-l-2 border-teal-500 pl-3 italic text-sm text-paper-700 leading-snug my-2">
                {p.body}
              </blockquote>
              {p.interpretation && (
                <p className="text-sm text-paper-900">→ {p.interpretation}</p>
              )}
            </div>
          ))}
        </Card>
      )}

      {/* Weather */}
      {e.weather && (
        <Card title="Wetter" source={(e.weather as any)._stubbed || (e.weather as any).source?.kind === 'stubbed' ? 'stub' : null}>
          <p className="text-md font-semibold mb-1">{(e.weather as any).location || 'Berlin'}</p>
          <p className="text-sm text-paper-700 mb-2">{(e.weather as any).forecast}</p>
          {(e.weather as any).relevant_because && (
            <p className="text-xs text-paper-500">{(e.weather as any).relevant_because}</p>
          )}
        </Card>
      )}

      {/* Legal */}
      {e.legal_context && e.legal_context.length > 0 && (
        <Card title="Rechtskontext">
          {e.legal_context.map((ref: any, i: number) => (
            <div key={i} className="mb-3 last:mb-0">
              <p className="text-sm font-semibold mb-1">{ref.citation}</p>
              <p className="text-sm text-paper-700 mb-1">{ref.short_text}</p>
              {ref.relevance && <p className="text-xs text-paper-500">{ref.relevance}</p>}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
