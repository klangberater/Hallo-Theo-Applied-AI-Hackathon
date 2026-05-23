// API client for the FastAPI backend. nginx mounts it at /api/* and strips
// that prefix before forwarding to :8002, so the browser path /api/tickets
// reaches the backend's /tickets handler.

export type DerivedState = 'open' | 'done' | 'archived';

export interface Ticket {
  id: string;
  unit_id: string | null;
  category: string | null;
  priority: string | null;
  status: string | null;
  opened_at: string | null;
  classified_intent: string | null;
  full_text: string | null;
  pattern_count: string | null;
  autonomy_mode: 'autonomous_done' | 'bundle_approve' | 'propose' | null;
  unit_label: string | null;
  tenant_name: string;
  channel: string | null;
  // Mark-as-Done & Archive feature.
  done_at: string | null;
  done_by: string | null;
  resolution_note: string | null;
  derived_state: DerivedState;
}

export interface SourceCitation {
  kind: string;
  id?: string | null;
  excerpt?: string | null;
}

export interface SuggestedAction {
  action_type: string;
  payload: Record<string, any>;
  rationale: string;
  source_citations?: SourceCitation[];
  confidence?: 'high' | 'medium' | 'low';
  bundle_id?: string | null;
  bundle_order?: number;
  executed_at?: string | null;
}

export interface EnrichmentPayload {
  tenant_card?: any;
  unit_card?: any;
  lease_facts?: string[];
  prior_incidents?: {
    count: number;
    timespan_months?: number;
    timeline: Array<{ date: string; fact: string; source?: SourceCitation }>;
    pattern_summary?: string;
    source?: string;
  };
  open_vendor_offers?: any[];
  internal_pre_approvals?: any[];
  weather?: any;
  legal_context?: any[];
  suggested_actions?: SuggestedAction[];
  autonomy_mode?: 'autonomous_done' | 'bundle_approve' | 'propose';
  autonomy_rationale?: string;
}

export interface TicketDetail extends Ticket {
  enrichment: EnrichmentPayload | null;
  suggested_actions: SuggestedAction[] | null;
  source_thread_id: string | null;
  property_name: string | null;
  property_address: string | null;
  tenant_email?: string | null;
  tenant_phone?: string | null;
  tenant_metadata?: any;
  lease_rent_cold?: string | null;
  lease_start?: string | null;
}

export interface ThreadMessage {
  id: string;
  thread_id: string;
  direction: 'inbound' | 'outbound';
  sender: string;
  body: string;
  sent_at: string;
}

export interface TraceEvent {
  step: number;
  kind: string;
  payload: Record<string, any>;
  created_at: string;
}

// In dev (`npm run dev`), call the production API directly. In prod the
// browser hits /api on the same origin.
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  (typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'https://getfletcher.ai'
    : '');

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}/api${path}`, { cache: 'no-store' });
  if (!r.ok) throw new Error(`GET ${path}: HTTP ${r.status}`);
  return (await r.json()) as T;
}

async function post<T>(path: string, body?: any): Promise<T> {
  const r = await fetch(`${API_BASE}/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`POST ${path}: HTTP ${r.status}`);
  return (await r.json()) as T;
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : '';
}

export const api = {
  listTickets: (view: 'inbox' | 'archive' = 'inbox', search?: string) =>
    get<Ticket[]>(`/tickets${qs({ view, search })}`),
  countOpen: () => get<{ count: number }>('/tickets/open-count'),
  getTicket: (id: string) => get<TicketDetail>(`/tickets/${id}`),
  getThread: (id: string) => get<ThreadMessage[]>(`/tickets/${id}/thread`),
  getTrace:  (id: string) => get<TraceEvent[]>(`/tickets/${id}/trace`),

  executeAction: (id: string, idx: number, bodyOverride?: string) =>
    post<{ ok: boolean; warning?: string }>(
      `/tickets/${id}/actions/${idx}/execute`,
      bodyOverride !== undefined ? { body_override: bodyOverride } : undefined,
    ),
  executeBundle: (id: string, bodyOverride?: string) =>
    post<{ ok: boolean; executed: number; warnings: string[]; error?: string }>(
      `/tickets/${id}/bundle/execute`,
      bodyOverride !== undefined ? { body_override: bodyOverride } : undefined,
    ),

  markDone: (id: string, resolutionNote?: string) =>
    post<{ ok: boolean; ticket_id: string; state: DerivedState }>(
      `/tickets/${id}/mark-done`,
      resolutionNote ? { resolution_note: resolutionNote } : {},
    ),
  reopen: (id: string) =>
    post<{ ok: boolean; ticket_id: string; state: DerivedState }>(
      `/tickets/${id}/reopen`,
    ),

  fireKoehler: () => post<any>('/demo/fire/koehler'),
  fireDemir:   () => post<any>('/demo/fire/demir'),
  resetDemo:   () => post<any>('/demo/reset'),
};

export function cx(...args: (string | undefined | false | null)[]): string {
  return args.filter(Boolean).join(' ');
}
