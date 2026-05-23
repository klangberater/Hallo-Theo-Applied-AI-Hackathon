# Theo Copilot — Product & Build Spec

> **Project:** AI-powered operations inbox for hallo theo
> **Event:** Property Operations Copilot Hackathon, Berlin, 48 hours
> **Status:** Build spec — written for the team building it, not for the pitch deck
> **Sponsor:** hallo theo (we are pitching a module that lives inside their platform, not a competing product)
> **Reads alongside:** `00_SZENARIO_BIBEL.md`, `01_kundenkomplaints_mapping.md`, `DEMO_SKRIPT_v2.md`, and the prior `PROPERTY_MGMT_MEMORY.md` architecture document this team produced earlier
> **Version:** Unified v3 — Postgres + server-side deployment

---

## 0. How to read this document

This is a build spec, not a vision document. It is structured around what you will and will not build by Sunday afternoon, with explicit reasoning for the cuts.

There are three layers:

- **L1 — Demo Surface.** What judges see in the 5-minute demo. Must work flawlessly. Builds Friday night through Saturday afternoon.
- **L2 — Built but not demoed.** Infrastructure and capabilities the demo rests on but does not foreground. Built Saturday.
- **L3 — Spec'd but not built.** The production architecture, used in pitch and Q&A only. Documented here, never claimed to be running.

Sections explicitly tag which layer each capability belongs to. **If a team member starts working on an L3 item before L1 is end-to-end, stop them.**

---

## 1. Product definition

### 1.1 What we are building

A property operations inbox built for hallo theo's Verwalter:innen. Tickets arrive from tenant channels (WhatsApp in this demo, easily extended to email, voicemail, portal). Each ticket auto-enriches with tenant context, property history, contracts, prior incidents, and the temporal pattern across all of it — so the operator sees not just *what was said* but *what it means*. The operator approves or edits AI-suggested actions and replies; the loop closes back to the tenant.

The reasoning layer (the Graphiti-backed temporal memory) is *inside* the product, surfacing as a "Pattern" panel on the ticket detail view. It is the technical moat but not the user-facing pitch — the user-facing pitch is **"every ticket arrives already understood."**

### 1.2 What we are explicitly not building

- A general inbox / unified communications platform (we ship WhatsApp as the one channel; others on roadmap)
- A tenant-facing app
- A multi-tenant SaaS shell (one PM, one property — Sarah Weber at Zossener 47)
- Auth, RBAC, audit log (beyond what we already have in the existing app)
- A property management system of record (hallo theo already has one)
- WEG / Eigentümerversammlung workflows (mentioned on roadmap, not demoed)
- A mobile app
- A multi-agent framework with named personas

### 1.3 The user

Sarah Weber, Senior Verwalterin at hallo theo Berlin. See `00_SZENARIO_BIBEL.md` for full persona. Key fact: she is a hallo theo employee, not a customer. The pitch is about making her 10× more capable, not replacing her.

### 1.4 The one-sentence value proposition

> Theo Copilot is the operations inbox for hallo theo: tenant messages arrive enriched with tenant context, property history, prior incidents, and contracts — and replies go back out approved by the Verwalter:in in under two minutes.

### 1.5 The hackathon-specific framing

The pitch frames Theo Copilot as a module that *fits inside* hallo theo, addressing the customer complaints (documented in `01_kundenkomplaints_mapping.md`) that hallo theo's existing platform has not yet closed. This framing is deliberate: it removes the "we already have AI" objection, and it positions the work as a collaboration proposal rather than a product pitch.

---

## 2. Architecture overview

### 2.1 The three memory layers (carried over from `PROPERTY_MGMT_MEMORY.md`)

This project commits to the three-layer memory architecture defined in the team's prior memory spec.

| Layer | Purpose | Tech | Layer of build |
|---|---|---|---|
| **L1 — Domain Wiki** | Stable domain facts: BGB excerpts, BetrKV reference, SOPs, templates | Markdown files in repo | Demo Surface (read by agent) |
| **L2 — Structured State** | Properties, units, leases, tickets, invoices, contacts, channel threads, messages | **Postgres** (existing instance on the team's server) | Demo Surface (queried by agent) |
| **L3 — Temporal Memory** | "How does this tenant behave over time," chronic-pattern facts, escalation history | **Graphiti + Neo4j (real, running, live during demo)** | **Demo Surface — the hero technical moat** |

This matches the prior memory spec's architecture exactly. One deliberate deviation:

**Layer 3 reads-from in the demo, not shadow mode.** The prior spec recommended Graphiti shadow-mode for 2-4 weeks before the agent reads from it. We violate this deliberately because the demo IS the read path. Mitigation: we curate the ingested episodes by hand from the dataset, we do not let the agent write to Graphiti during the demo, and we pre-validate all queries Friday night.

### 2.2 The runtime stack — server-side deployment

Everything runs on the team's existing server. Demo laptop talks to it via browser only.

```
                                      DEMO LAPTOP
                                      ┌──────────┐
                                      │ Browser  │
                                      └────┬─────┘
                                           │ HTTPS (or SSH tunnel)
                                           │ — single connection
                                           ▼
═══════════════════════════════════════════════════════════════
                  TEAM SERVER (all services local to each other)
═══════════════════════════════════════════════════════════════
   ┌────────────────────────────────────────────────────────┐
   │  Streamlit (port 8501)                                  │
   │  - Phone mockup, inbox, ticket detail, trace panel      │
   └─────────────────────┬──────────────────────────────────┘
                         │
                         ▼
   ┌────────────────────────────────────────────────────────┐
   │  FastAPI intake service (port 8000)                     │
   │  - /webhook/whatsapp endpoint (stubbed)                 │
   │  - Tenant lookup, ticket creation                       │
   │  - Triggers Graphiti episode + enrichment loop          │
   └─────────────────────┬──────────────────────────────────┘
                         │
                         ▼
   ┌────────────────────────────────────────────────────────┐
   │  Enrichment agent loop (Python, Anthropic SDK)          │
   │  - claude-sonnet-4-6 for intent classification          │
   │  - claude-opus-4-7 for enrichment reasoning             │
   │  - Tool-use loop, no agent framework                    │
   │  - Produces typed structured enrichment payload         │
   └──┬───────────┬───────────┬───────────┬─────────────────┘
      │           │           │           │
      ▼           ▼           ▼           ▼
   ┌──────┐  ┌──────────┐  ┌────────┐  ┌─────────────────┐
   │ L1   │  │ L2       │  │ L3     │  │ External        │
   │ Wiki │  │ Postgres │  │ Neo4j  │  │ - Weather (stub)│
   │ (md) │  │ (local)  │  │ (local)│  │ - Chat (json)   │
   └──────┘  └──────────┘  └────────┘  └─────────────────┘
═══════════════════════════════════════════════════════════════

   Network dependency on demo day: ONE browser → server connection
```

### 2.3 Why this stack and not the alternatives

- **No LangChain, CrewAI, AutoGen, or LangGraph.** We have 48 hours and our judge cares about business viability. A framework is a learning curve we cannot afford. Raw Anthropic SDK + a tool loop in 80 lines of Python is faster to write, easier to debug under pressure, and demos identically.
- **Postgres on the existing server (not local SQLite, not a new Postgres):** zero setup cost, the team uses it daily, the schema migration is straightforward, JSONB columns are native. Production-realistic and demo-safe.
- **No vector database (separate from Graphiti).** Graphiti gives us hybrid search built-in. We do not need a parallel pgvector or Chroma instance.
- **Streamlit, not Next.js / React.** Backend-strong team, no frontend specialist. Streamlit lets one person build the entire UI in a day and still look credible. It will look like an internal tool, which is exactly what Theo Copilot is — that's a feature, not a bug. If the team has a strong frontend person, Next.js is acceptable but adds 4-6 hours of risk.
- **Everything colocated on the team's server.** Removes network dependencies between services. The only network hop on demo day is browser → server, which is one HTTPS connection that handles wifi blips gracefully.

### 2.4 Database namespacing inside the existing Postgres

Since Theo Copilot tables live alongside the team's existing app schema, isolate them cleanly:

```sql
CREATE SCHEMA IF NOT EXISTS theo;
SET search_path TO theo, public;
```

All Theo Copilot tables get created in the `theo` schema. The team's existing app tables remain in `public` (or wherever they live) and are unaffected. If the existing app already has `properties` / `tenants` / `units` etc. — **do reuse them**. Add Theo's tables (`tickets`, `channel_threads`, `enrichment_*`) and reference the existing entities via foreign keys.

A decision worth making Friday morning: does Theo Copilot create its own `tenants` and `properties` tables, or join against the existing app's? Reusing existing tables is faster but tightly couples the demo to whatever state the existing schema is in. Decide and document.

---

## 3. The demo workflow

There is one primary workflow with two ticket variants. The product is the same; what differs is the kind of ticket and the kind of action it triggers.

### 3.1 The primary workflow — "ticket lifecycle"

This is the demo's spine. The product *is* this workflow.

**Phase A — Intake (channel side, ~30 seconds of demo time)**

- A WhatsApp conversation is shown on a phone-shaped mockup on screen. Frau Köhler types her message.
- The message arrives at hallo theo's WhatsApp Business number.
- An ingestion service parses the message:
  - Identifies the sender by phone number → links to a tenant in L2
  - Determines the unit and property from the tenant record
  - Classifies the message intent ("maintenance: heating") using Claude Sonnet
  - Creates a `tickets` row with status `open`, `triaged=true`
  - Writes an `episode` to Graphiti tagged with the tenant's group_id (this updates the temporal memory immediately)

**Phase B — Operator view (~3 minutes of demo time, the meat)**

- Sarah's inbox view shows the new ticket at the top, with a small "🔥 Pattern detected" marker added by the enrichment step.
- She clicks the ticket. The detail view opens. Three columns:
  - **Left:** Ticket thread — the original WhatsApp message and any prior thread (auto-pulled from the channel history if applicable).
  - **Center:** The conversation continuation — empty for now, where Sarah will see the AI-drafted reply and approve/edit it.
  - **Right:** **Enrichment panel** — auto-populated cards: tenant card, unit card, lease key facts, prior incidents (the Graphiti-fed timeline), open vendor offers, internal pre-approvals from chat, weather forecast where relevant.
- The right-side enrichment is the visual signature. Each card cites its source. The "prior incidents" card is a small timeline visualization showing the 6 heating incidents and the unapproved Bergmann offer — **this is the Graphiti moment**.

**Phase C — Suggested action and reply (~60 seconds of demo time)**

- Below the enrichment, a "Suggested actions" section appears.
- For Frau Köhler's heating ticket: three proposed actions stacked.
  1. Dispatch Bergmann (vendor card, ETA, full reasoning)
  2. Approve open Bergmann offer (with link to Jonas's pre-approval message)
  3. Drafted WhatsApp reply to Frau Köhler (German, warm, with concrete timing)
- Sarah skims, edits one sentence in the drafted reply (personalizes), clicks **Approve & Send**.
- The reply visibly sends back through WhatsApp. The ticket status updates: `awaiting_vendor`, with Bergmann dispatched and the offer approved logged in the timeline.

**Phase D — Closure (omitted from demo, mentioned)**

Status updates as Bergmann confirms, completes work, and the ticket closes — not shown live, but mentioned: "and the loop closes when Bergmann reports back."

### 3.2 The secondary ticket — variation, not repetition

To show the product is general, **briefly** demo one more ticket type — the Demir Nebenkostenabrechnung dispute. Same UI, different content:

- Email channel (briefly mentioned: "the system also handles email — here's an email-originated ticket")
- Enrichment shows: lease, NK 2024 abrechnung, gas price data, prior years' abrechnungen
- Suggested action: drafted German defense letter with a comparison table
- Sarah approves, the letter sends as an email reply

This takes ~45 seconds of demo time. It exists to prove the product is not a one-trick demo. **If time is tight on Saturday, cut this and mention it verbally instead.**

### 3.3 The third workflow — FixDirekt anomaly (de-prioritized)

The vendor anomaly detection workflow from the prior spec still exists conceptually but **drops out of the live demo** in this v2. It appears in the inbox queue as a system-generated ticket but Sarah doesn't open it during the demo. Mention in the pitch: "Theo also generates system tickets — like this one, where it flagged a vendor invoice pattern anomaly proactively."

Build it only if Saturday afternoon has spare capacity.

---

## 4. The autonomy spectrum

This is a slide in the pitch and a real product decision. Every capability above maps to one of three modes:

| Mode | Definition | Example |
|---|---|---|
| **Autonomous** | Theo acts and informs | Acknowledgment of receipt to known categories, system-generated tickets for anomalies |
| **Collaborative** | Theo proposes, Sarah approves | Vendor dispatch, tenant communications, financial approvals, NK defense letters |
| **Assisted** | Theo researches and surfaces; Sarah decides | Lease renewal pricing, legal/regulatory questions, sensitive escalations |

Every action in the demo is **collaborative or assisted**. Autonomous actions in the demo are deliberately minor (acknowledgments, anomaly tickets) so that the autonomy story is honest. This is the inverse of how most teams will frame their demos and it lands well with judges who have seen too many "AI auto-pilot" pitches.

---

## 5. Tool surface (the agent's vocabulary)

These are the functions the agent has access to via Anthropic tool use. Backend builds these as Python functions; the agent loop dispatches.

### 5.1 L2 tools (Postgres queries via SQLAlchemy or asyncpg)

```python
def get_unit(unit_id: str) -> Unit
def get_tenant(tenant_id: str) -> Tenant
def get_tenant_by_phone(phone: str) -> Tenant | None
# Lookup tenant by E.164 phone for WhatsApp message routing

def get_lease(unit_id: str) -> Lease  # returns excerpt of relevant clauses
def list_tickets(unit_id: str, since: date | None = None) -> list[Ticket]
def get_ticket(ticket_id: str) -> Ticket  # full detail
def list_invoices(vendor_id: str | None = None, unit_id: str | None = None) -> list[Invoice]
def get_invoice(invoice_id: str) -> Invoice
def get_nka(unit_id: str, year: int) -> Nebenkostenabrechnung
def get_vendor(vendor_id: str) -> Vendor
def get_open_offers(unit_id: str | None = None, vendor_id: str | None = None) -> list[VendorOffer]

def get_thread(channel: str, external_thread_id: str) -> Thread | None
# Get conversation thread (prior WhatsApp messages, prior email replies)

def list_internal_chat(thread_id: str | None = None, since: datetime | None = None) -> list[ChatMessage]
def list_tickets_for_operator(operator_id: str, status: str | None = None) -> list[TicketSummary]
# The inbox feed

def get_ticket_with_enrichment(ticket_id: str) -> EnrichedTicket
# The ticket detail view — returns ticket + all enrichment cards + suggested actions

def get_weather_forecast(location: str, days_ahead: int) -> Forecast  # stubbed
```

### 5.2 L1 tools (wiki retrieval)

```python
def search_wiki(query: str) -> list[WikiSnippet]  # semantic over markdown
def read_wiki_page(path: str) -> str
```

For the hackathon, `search_wiki` is a simple BM25 over markdown files. We do not need embeddings here; the wiki has maybe 20 documents.

### 5.3 L3 tools (Graphiti — the hero)

```python
def query_temporal_memory(
    query: str,
    group_id: str,       # e.g. "tenant:koehler_we4l" or "property:zossener_47"
    num_results: int = 10
) -> list[TemporalFact]
# Returns facts with fact text, valid_from, valid_until, source episodes.

def get_entity_timeline(
    entity_name: str,
    group_id: str
) -> list[Episode]
# Returns chronologically-ordered episodes mentioning this entity.
```

We do **not** expose `add_episode` to the agent in the demo runtime. Episodes are pre-ingested (and additionally written by the intake service when a new message arrives — but never by the agent itself). In production this would be wrapped through the candidates table described in the prior memory spec.

### 5.4 Action execution tools

These **execute** approved actions on real fake channels (writes to Postgres, with UI rendering the effect):

```python
def send_whatsapp_reply(thread_id: str, body: str) -> SentMessage
# Sends to a stub WhatsApp service. In the demo this:
# - inserts into theo.channel_messages with direction='outbound'
# - the WhatsApp mockup UI on the phone-shaped device polls and renders it

def send_email_reply(thread_id: str, subject: str, body: str) -> SentMessage
# Same pattern for email

def dispatch_vendor(vendor_id: str, scope: str, urgency: str) -> DispatchRecord
# Creates a vendor_dispatches row and a stub "notified Bergmann" event in the trace

def approve_offer(offer_id: str) -> ApprovalRecord
# Updates vendor_offers.status to 'approved'
```

**Important:** these tools still only run after Sarah clicks **Approve & Send** in the UI. The agent prepares the drafts; the UI is the gate.

---

## 6. Data layer — concrete shapes

### 6.1 L2 schema (Postgres)

Create everything under the `theo` schema for clean separation from the existing app:

```sql
CREATE SCHEMA IF NOT EXISTS theo;
SET search_path TO theo, public;

-- Core entities (reuse existing app tables if available; otherwise create)
CREATE TABLE IF NOT EXISTS properties (
    id TEXT PRIMARY KEY,
    name TEXT,
    address TEXT,
    owner TEXT,
    metadata JSONB
);
CREATE TABLE IF NOT EXISTS units (
    id TEXT PRIMARY KEY,
    property_id TEXT REFERENCES properties(id),
    label TEXT,
    qm REAL,
    type TEXT
);
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    metadata JSONB
);
CREATE TABLE IF NOT EXISTS leases (
    id TEXT PRIMARY KEY,
    unit_id TEXT REFERENCES units(id),
    tenant_id TEXT REFERENCES tenants(id),
    start_date DATE,
    end_date DATE,
    rent_cold NUMERIC(10,2),
    status TEXT,
    full_text TEXT
);
CREATE TABLE IF NOT EXISTS vendors (
    id TEXT PRIMARY KEY,
    name TEXT,
    trade TEXT,
    status TEXT,
    contract_until DATE,
    notes TEXT
);

-- Events / artifacts
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    unit_id TEXT REFERENCES units(id),
    category TEXT,
    priority TEXT,
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    resolution TEXT,
    cost NUMERIC(10,2),
    vendor_id TEXT REFERENCES vendors(id),
    full_text TEXT,
    source_thread_id TEXT,
    classified_intent TEXT,
    status TEXT,                    -- 'open', 'enriching', 'ready_for_review',
                                    -- 'awaiting_vendor', 'awaiting_tenant', 'closed'
    enrichment JSONB,               -- cached enrichment payload
    suggested_actions JSONB
);

CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    vendor_id TEXT REFERENCES vendors(id),
    unit_id TEXT REFERENCES units(id),
    amount_brutto NUMERIC(10,2),
    issued_at DATE,
    line_items TEXT,
    raw_text TEXT,
    has_itemization BOOLEAN
);
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    from_address TEXT,
    to_address TEXT,
    subject TEXT,
    body TEXT,
    received_at TIMESTAMPTZ,
    thread_id TEXT,
    unit_id TEXT
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT,
    sender TEXT,
    body TEXT,
    sent_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS nka (
    id TEXT PRIMARY KEY,
    unit_id TEXT REFERENCES units(id),
    year INTEGER,
    total NUMERIC(10,2),
    breakdown JSONB,
    raw_text TEXT
);
CREATE TABLE IF NOT EXISTS vendor_offers (
    id TEXT PRIMARY KEY,
    vendor_id TEXT REFERENCES vendors(id),
    unit_id TEXT REFERENCES units(id),
    scope TEXT,
    amount NUMERIC(10,2),
    status TEXT,
    issued_at DATE
);

-- Channel-side state
CREATE TABLE IF NOT EXISTS channel_threads (
    id TEXT PRIMARY KEY,
    channel TEXT,                    -- 'whatsapp', 'email', 'voicemail', 'portal'
    external_id TEXT,                -- WhatsApp chat id, email thread id
    tenant_id TEXT REFERENCES tenants(id),
    unit_id TEXT REFERENCES units(id),
    last_message_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS channel_messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT REFERENCES channel_threads(id),
    direction TEXT,                  -- 'inbound', 'outbound'
    sender TEXT,
    body TEXT,
    sent_at TIMESTAMPTZ,
    media_attachments JSONB
);

CREATE TABLE IF NOT EXISTS vendor_dispatches (
    id SERIAL PRIMARY KEY,
    ticket_id TEXT REFERENCES tickets(id),
    vendor_id TEXT REFERENCES vendors(id),
    scope TEXT,
    urgency TEXT,
    dispatched_at TIMESTAMPTZ
);

-- Action proposals (the agent writes here; Sarah approves)
CREATE TABLE IF NOT EXISTS proposed_actions (
    id SERIAL PRIMARY KEY,
    proposed_at TIMESTAMPTZ,
    action_type TEXT,
    payload JSONB,
    rationale TEXT,
    status TEXT                      -- 'pending', 'approved', 'rejected', 'edited'
);

-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_unit ON tickets(unit_id);
CREATE INDEX IF NOT EXISTS idx_channel_messages_thread ON channel_messages(thread_id, sent_at);
CREATE INDEX IF NOT EXISTS idx_tenants_phone ON tenants(phone);
```

The enrichment payload (stored in `tickets.enrichment` as JSONB) is the central typed artifact. Shape:

```json
{
  "tenant_card": { "name": "...", "since": "...", "warnings": [...] },
  "unit_card": { "label": "...", "qm": ..., "lease_status": "..." },
  "lease_facts": [...],
  "prior_incidents": {
    "count": 6,
    "timespan_months": 18,
    "timeline": [ {"date": "...", "fact": "...", "source_id": "..."}, ... ],
    "pattern_summary": "Same root cause: thermostat ventil, all unresolved...",
    "source": "graphiti"
  },
  "open_vendor_offers": [...],
  "internal_pre_approvals": [...],
  "weather": {...},
  "legal_context": [...]
}
```

Seed data comes directly from the existing dataset (`hallotheo_demo/`). Write a one-off loader script Friday night that runs against the dev Postgres.

### 6.2 L3 schema (Graphiti)

Graphiti manages its own Neo4j schema. We control it via:

**Group IDs (Graphiti's multi-tenancy primitive):**
- `tenant:<tenant_id>` — facts about a specific tenant
- `property:<property_id>` — building-wide facts
- `vendor:<vendor_id>` — vendor performance facts

**Episode types we will ingest:**
- `maintenance_incident` (ticket text + outcome)
- `tenant_communication` (email, WhatsApp message, or letter)
- `legal_event` (Mietminderung claim, lease addendum)
- `internal_note` (Sarah's notes, chat threads)
- `vendor_interaction` (invoices, offers, communications)

For the Köhler hero query specifically, we need at least these episodes ingested before demo:

| Episode name | Type | reference_time | Group | Source text |
|---|---|---|---|---|
| heating-incident-2024-10 | maintenance_incident | 2024-10-12 | tenant:koehler_we4l, property:zossener_47 | VG-2024-0188 text |
| heating-incident-2024-12 | maintenance_incident | 2024-12-02 | same | VG-2024-0233 text |
| heating-incident-2025-01 | maintenance_incident | 2025-01-22 | same | VG-2025-0021 text |
| mietminderung-2025-02 | legal_event | 2025-02-12 | tenant:koehler_we4l | VG-2025-0058 text |
| medical-addendum-2024-05 | legal_event | 2024-05-18 | tenant:koehler_we4l | lease addendum text |
| heating-incident-2025-04 | maintenance_incident | 2025-04-18 | same | VG-2025-0142 text |
| bergmann-offer-2025-04 | vendor_interaction | 2025-04-18 | property:zossener_47, vendor:bergmann | offer text |
| whatsapp-2025-11-koehler | tenant_communication | 2025-11-17 | tenant:koehler_we4l | whatsapp_01 text (written by intake on demo day) |

When the agent calls `query_temporal_memory("Köhler heating issues", group_id="tenant:koehler_we4l")`, Graphiti will return facts like:
- "Margarethe Köhler reported heating failure in living room" — valid 2024-10-12 → ongoing
- "Living room heater thermostat malfunction is recurring" — valid 2024-12-02 → ongoing
- "Margarethe Köhler has medical heat sensitivity" — valid 2024-05-18 → ongoing
- "Bergmann offered thermostat replacement for 340 EUR" — valid 2025-04-18 → ongoing, status "unapproved"

This is the magic of Graphiti: it derives these structured facts from the raw episode text using its LLM extraction. We don't write the facts — Graphiti reads our texts and structures them.

### 6.3 Graphiti episodes from WhatsApp intake

The WhatsApp intake creates an episode immediately on message arrival:

```python
await graphiti.add_episode(
    name=f"whatsapp-{ticket_id}",
    episode_body=message.body,
    source=EpisodeType.message,
    source_description=f"WhatsApp from {tenant.name} on {date}",
    reference_time=message.sent_at,
    group_ids=[f"tenant:{tenant.id}", f"property:{property.id}"]
)
```

In production the agent would *also* propose candidate facts after handling the ticket (per the prior memory spec's reconciliation queue). For the demo, the ingestion of the raw episode is enough — Graphiti's LLM extraction picks up the entities and relations on its own.

### 6.4 L1 — the wiki

Minimal, ~6 files. Written by us, in German where it would be in production.

```
domain-wiki/
  index.md
  policies/
    heating-emergency-de.md          # Heizperiode, BGB §535/536, response times
    mietminderung-handling-de.md     # how to evaluate and respond
    vendor-payment-rules.md          # itemization requirements, when to escalate
  procedures/
    nka-defense-de.md                # how to defend a NK abrechnung
    vendor-anomaly-de.md             # template for requesting itemization
  templates/
    tenant-acknowledgment-de.md
    vendor-dispatch-de.md
```

Each file ~200 words. Written in German because the agent should respond to Sarah in her working language, and German legal references should appear verbatim.

---

## 7. The agent flow for ticket enrichment

The agent is triggered by ticket arrival, not by user click. Sequence:

```
WhatsApp message arrives
  ↓
Webhook (stubbed) → ingestion service
  ↓
Identify tenant by phone, create ticket (status='open')
  ↓
Add episode to Graphiti (status='enriching')
  ↓
Run the enrichment agent loop:
  • read ticket body
  • identify intent (heating / NK / payment / noise / etc.)
  • call L2 tools to fetch tenant, unit, lease, prior tickets, open offers
  • call L3 (Graphiti) to query temporal patterns for this tenant
  • call L1 wiki to pull relevant policy (heating-emergency-de.md)
  • call internal-chat tool to find any pre-approvals
  • call weather tool if relevant
  • compose enrichment payload (typed structure, NOT free text)
  • compose suggested actions with rationale per action
  ↓
Write enrichment + suggested_actions to ticket row (status='ready_for_review')
  ↓
Sarah's inbox updates (push or short poll)
```

The agent does NOT free-form generate the entire UI. It produces a **structured enrichment payload** in JSON, which the frontend renders into typed cards. This matters because:

1. The UI is deterministic and renders fast — judges see polished cards, not a wall of text
2. The agent can be wrong about one card without breaking the rest
3. Each card carries a `source` citation that the UI renders consistently

### 7.1 Intent classification step (Sonnet)

The very first thing the agent does after ticket creation is intent classification, because intent gates which other tools get called. Use Sonnet here (cheap, fast):

```python
def classify_intent(message_body: str) -> dict:
    # Returns: { intent: 'heating' | 'nka_dispute' | 'noise' | 'payment' | 'other',
    #            urgency: 'emergency' | 'urgent' | 'standard',
    #            confidence: 0-1 }
```

Then the main reasoning loop uses Opus. The split saves time and money without sacrificing the moments that matter.

### 7.2 The enrichment loop (Opus)

A single Python function. Pseudocode:

```python
def enrich_ticket(ticket_id: str) -> EnrichmentPayload:
    """
    Triggered by intake service after ticket creation.
    Produces a typed enrichment payload + suggested actions.
    """
    ticket = db.get_ticket(ticket_id)

    # 1. System prompt with persona, tools, output format
    system = build_enrichment_system_prompt(ticket.classified_intent)

    # 2. Initial user message
    messages = [{"role": "user", "content": render_enrichment_intent(ticket)}]

    # 3. Tool-use loop
    while True:
        response = client.messages.create(
            model="claude-opus-4-7",     # Opus for reasoning quality
            max_tokens=4096,
            tools=TOOL_SCHEMAS,
            messages=messages,
            system=system,
        )

        # Capture the reasoning trace as we go
        log_trace_step(ticket_id, response)

        if response.stop_reason == "end_turn":
            # Final response contains the structured payload
            return parse_enrichment_payload(response)

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = TOOL_DISPATCH[block.name](**block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue
```

Notes:
- Model choice: Opus for the reasoning quality and trace clarity. Sonnet would be 4× cheaper but for a demo with judges watching, the slight quality edge matters and total cost is trivial (~$3 across the demo).
- We do not stream. Streaming complicates the trace UI and saves us ~3 seconds at the cost of a more complex implementation. Cut it.
- The trace is captured by writing each `tool_use` and its `tool_result` to a session log. The UI reads that log to render the trace panel.

### 7.3 System prompt skeleton

```
You are Theo Copilot, the operations layer for hallo theo, a German digital
property management company. You enrich incoming tenant tickets so that
Sarah Weber, the Verwalterin, can act on them in under two minutes.

Your job is to take a new ticket and produce a structured enrichment
payload covering: tenant context, unit/lease facts, prior incidents and
patterns, open vendor offers, relevant internal pre-approvals, weather
where relevant, and legal context where relevant.

You have three classes of tools:
- L1 (wiki): stable domain knowledge, laws, SOPs, templates
- L2 (state): current facts about properties, units, leases, tickets, invoices
- L3 (memory): temporal facts — what we have learned about a tenant or
  property over time, including chronic patterns and prior legal events

Always reason BEFORE proposing actions. Each enrichment card and each
suggested action must cite the specific source documents that supported it.

You PROPOSE actions for Sarah to approve. You never execute. The draft_*
tools write to a proposal queue that the UI surfaces for human approval.

You write in German when drafting tenant or vendor communications. You
respond to Sarah in [LANGUAGE — toggle here]. Legal references use German
paragraph notation (§ 535 BGB, BetrKV §7, etc.).

Important behaviors:
- Always check temporal memory (L3) when handling a tenant or property
  situation. Chronic patterns matter more than the current incident in
  isolation.
- Always check internal chat (L2 tool) before recommending an action that
  might already be pre-approved or vetoed.
- When you don't have enough information, say so and propose a research
  step rather than fabricating.
- Your final response must be a valid JSON object matching the
  EnrichmentPayload schema. Do not include explanatory prose outside
  the JSON.
```

---

## 8. The frontend — three views

Built with Streamlit (one Python file per view, shared session state). If using Next.js, same view structure.

### View 1: The phone-shaped WhatsApp mockup (the intake demo)

On the left of the screen during the intake phase, a phone-shaped div renders the WhatsApp conversation. Bubbles appear typed-out for the demo (timed JS reveal). At the moment of "send," a flash + the phone moves to the side; the operator's inbox appears.

This is **theater**, not a real WhatsApp client. Fake it well. A CSS phone-shape with two message bubbles is enough.

### View 2: The inbox

Familiar Front/Missive pattern. Three columns:

```
┌──────────────┬─────────────────────────────────────────┐
│  TICKET LIST │  TICKET DETAIL                          │
│              │                                         │
│ 🔥 Köhler    │  ┌──────────────┬─────────────────────┐ │
│   WhatsApp   │  │  Conversation│  Enrichment         │ │
│   2m ago     │  │              │                     │ │
│              │  │  Frau Köhler:│  📍 Tenant          │ │
│ • Demir      │  │  "Die Heizung│   Margarethe Köhler │ │
│   Email      │  │  im Wohn... "│   WE 4l, since 1997 │ │
│   3h ago     │  │              │   ⚠ Rent-stabilized │ │
│              │  │  [draft below│   ⚠ Medical addendum│ │
│ • FixDirekt  │  │   the line]  │                     │ │
│   System     │  │              │  🔁 Pattern         │ │
│   1d ago     │  │  Theo draft: │   6 incidents 18mo  │ │
│              │  │  "Liebe Frau │   [timeline viz]    │ │
│              │  │  Köhler, ..."│   Same root cause   │ │
│              │  │              │                     │ │
│              │  │  [edit][send]│  💰 Open offer      │ │
│              │  │              │   Bergmann 340€     │ │
│              │  │              │   Pending 7 months  │ │
│              │  │              │                     │ │
│              │  │              │  💬 Pre-approval    │ │
│              │  │              │   Jonas, Fri 16:22  │ │
│              │  │              │   "up to 500€"      │ │
│              │  │              │                     │ │
│              │  │              │  🌡 Weather         │ │
│              │  │              │   Frost Thu-Sun     │ │
│              │  │              │                     │ │
│              │  │              │  ⚖ Legal context    │ │
│              │  │              │   BGB §535/536      │ │
│              │  │              │   Heizperiode active│ │
│              │  └──────────────┴─────────────────────┘ │
│              │                                         │
│              │  ┌──────────────────────────────────────│
│              │  │  Suggested actions                   │
│              │  │  ① Dispatch Bergmann [why?]          │
│              │  │  ② Approve offer #BH-2025-0044       │
│              │  │  ③ Send drafted WhatsApp reply       │
│              │  │  [Approve all & Send] [Edit each]    │
│              │  └──────────────────────────────────────│
└──────────────┴─────────────────────────────────────────┘
```

The "🔁 Pattern" card is where Graphiti shines. The timeline visualization is what makes "temporal memory" visible.

### View 3: The reasoning trace (behind a "Why?" toggle)

Every enrichment card has a "Why?" link. Clicking expands the trace: every tool call, every source. This is for the curious — and for the Q&A where someone asks "but how does it know that?"

---

## 9. Deployment

### 9.1 Where everything runs

Everything runs on the team's existing server. Add three services (or whatever you call your existing orchestration unit):

1. **Streamlit app** — port 8501 (or behind your existing reverse proxy)
2. **FastAPI intake** — port 8000
3. **Neo4j** — port 7687 (bolt), 7474 (browser). Docker container, data volume mounted for persistence.

Postgres is already running. Add the `theo` schema to your existing database.

### 9.2 Recommended Docker Compose addition

Append to your existing `docker-compose.yml` (or create one if not present):

```yaml
services:
  neo4j:
    image: neo4j:5.26
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
    ports:
      - "127.0.0.1:7687:7687"      # bolt — bind to localhost only
      - "127.0.0.1:7474:7474"      # browser UI — useful for debugging, demo flex
    volumes:
      - neo4j_data:/data

  theo-intake:
    build: ./theo-copilot/intake
    environment:
      - DATABASE_URL=${THEO_DATABASE_URL}
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    ports:
      - "127.0.0.1:8000:8000"      # localhost only — exposed via reverse proxy or SSH tunnel
    depends_on:
      - neo4j

  theo-app:
    build: ./theo-copilot/app
    environment:
      - DATABASE_URL=${THEO_DATABASE_URL}
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - THEO_INTAKE_URL=http://theo-intake:8000
    ports:
      - "127.0.0.1:8501:8501"      # localhost only
    depends_on:
      - neo4j

volumes:
  neo4j_data:
```

Why `127.0.0.1:` prefixes everywhere: keeps these services off the public internet. Access via your existing reverse proxy (which probably handles TLS and auth for your main app), or via SSH tunnel for the demo browser. This avoids accidentally exposing the in-progress hackathon to the internet (and to any rando hitting Anthropic API spend).

### 9.3 Access from the demo laptop

Two options, pick one Friday:

**Option A — SSH tunnel (recommended).** Demo laptop runs:
```
ssh -L 8501:localhost:8501 user@server
```
Then browser → `http://localhost:8501`. Zero exposure. If wifi drops, browser stays connected to the tunnel (SSH reconnects on its own up to a point). If wifi dies entirely for >2 min, may need to re-establish the tunnel.

**Option B — through existing reverse proxy.** Add a subdomain (e.g. `theo.yourdomain.com`) to whatever proxies your main app. Protect with HTTP Basic Auth at least. Browser hits the public URL directly.

Option A is faster to set up and safer; Option B looks more polished if you have a wildcard cert already. Either works.

### 9.4 Workflow during the build

The team is already developing against this server-Postgres setup, so leverage that:

- Each team member's branch deploys to the server via your existing deployment flow
- Reset state between dry runs with a `scripts/reset_demo_state.py` (truncates `theo.*` tables, re-runs seed, re-ingests Graphiti episodes)
- Keep one tmux session on the server running the services + tails logs, so anyone can `ssh server` and see what's happening

---

## 10. Build plan — 48 hours

Hard rule: end-to-end vertical slice before any depth.

### Friday evening (4 hours, 19:00–23:00)

Four parallel slices. Each ships a hello-world by 23:00.

- **Lead 1 (Graphiti owner):** stand up Neo4j on the server via Docker Compose, install graphiti-core in the project, get a hello-world `add_episode` + `search` working from a script on the server. Verify with one Köhler episode. **No other work until this is done.**
- **Lead 2 (Agent/enrichment owner):** scaffold the enrichment agent loop, with `classify_intent` and the structured-output enrichment payload. Hello-world: a hardcoded WhatsApp body in, an enrichment JSON out (with stubbed tool returns).
- **Lead 3 (Data + intake owner):** Postgres `theo` schema migration. Build a `/webhook/whatsapp` endpoint (FastAPI single file) that accepts a fake WhatsApp webhook payload and runs intake. Seed loader script reading the existing dataset into Postgres.
- **Lead 4 (Frontend owner):** Streamlit shell, three views. **Friday night target: ticket list + ticket detail static with hardcoded enrichment JSON. Make it look credible.** Prioritize structure over polish.

Fifth track for anyone with a spare hour: the phone-shaped WhatsApp mockup. Pure HTML/CSS, no logic. Easy hire-out task.

### Saturday morning (8:00–13:00)

- **Graphiti owner:** ingest all 8 episodes from §6.2. Manually verify the temporal queries return what we expect. Document the exact query strings the demo will run. **Populate the kill-switch cache** (see §12.1) as part of this — when a query works, save the result as JSON.
- **Agent owner:** wire all L2 tools, wire the L1 wiki search, wire the Graphiti tool. Run a Köhler scenario end-to-end from a real intake event. Verify the agent produces a valid EnrichmentPayload.
- **Data owner:** write the 6 wiki markdown files in German. Wire the WhatsApp intake to the agent loop. Verify the intake → ticket → enrichment chain runs.
- **Frontend owner:** wire the inbox to read from Postgres. Build the enrichment card renderer (typed cards from JSONB). Build the Pattern card timeline visualization.

### Saturday afternoon (13:00–19:00) — the demo loop

- The Köhler workflow running end to end against real Graphiti and real Postgres.
- One person does a dry run with a stopwatch every 90 minutes.
- Fix the worst thing each run.
- If primary workflow is solid by 17:00, add the Demir secondary ticket.

### Saturday evening (19:00–23:00) — lockdown

- No new features. Polish the trace UI, polish the German text, polish the briefing format.
- Record a backup video of the full demo. Upload to a known URL.
- Verify the kill-switch path works (toggle the feature flag, confirm demo still runs).
- **Test SSH tunnel / reverse proxy access from the demo laptop with real wifi conditions.**

### Sunday morning (8:00–12:00)

- Pitch deck.
- Rehearse the pitch five times, timed.
- Final dry run of the demo at 11:30. Whatever's broken at 11:30 we don't fix; we route around.

### Sunday afternoon

- Pitch.

---

## 11. What the prior memory spec defines that we are NOT building

The prior `PROPERTY_MGMT_MEMORY.md` defines several pieces that are correctly part of the production architecture but explicitly out of scope for this build. **These belong in the pitch as L3 (Spec'd but not built), and the team should be ready to discuss them in Q&A.**

- **`memory_candidates` table + reconciliation job.** In production, the agent proposes candidate facts to L3 via Postgres; a batch job and a human review them before promotion to Graphiti. We skip this because (a) we pre-ingest known-good episodes, and (b) the agent never writes to L3 in the demo. In Q&A: "for production, the agent doesn't write directly to memory; it proposes candidates that go through a reconciliation queue with human spot-check. That's how we avoid hallucinations becoming memory."
- **Multi-tenancy at company level.** Hackathon assumes one Hausverwaltung (hallo theo). Production needs `tenant_id` (= PM company) above `customer_id` (= tenant person). Graphiti's group_ids handle this naturally; Postgres would need an extra column.
- **GDPR right-to-erasure propagation.** A production spec must propagate deletion through all three layers including the temporal memory. Out of scope for the demo, addressed in the pitch deck "Data & GDPR" slide.
- **Shadow-mode operation before L3 reads go live.** Spec'd in the prior document, deliberately skipped here because the demo IS the read path. In Q&A: "in real deployment we'd run Graphiti in shadow mode for 2-4 weeks to validate facts before the agent reads from it. For the demo we curated the ingested episodes by hand."

---

## 12. Risks and mitigations

### 12.1 The kill-switch: what if Graphiti misbehaves on stage?

If by Saturday 18:00 Graphiti queries are not reliably returning useful results in under 3 seconds, we execute Plan B:

- The Pattern card has a backup: the Postgres `tickets` table can be queried for the 6 prior incidents and rendered into the same timeline visualization.
- The agent loop has a feature flag: `USE_LIVE_GRAPHITI = False`. When false, the L3 tool function returns from a pre-computed JSON cache that mirrors what Graphiti returned during a successful Friday-night dry run.
- The user-visible UI is identical; the "powered by temporal memory" claim becomes weaker.
- If forced into this fallback, the pitch shifts slightly: "the Pattern card here is rendered from structured queries; in production we use Graphiti for cross-source fact extraction so this works on emails, voice memos, and unstructured documents — let me show you that running separately." Then demo Graphiti as a standalone after the formal pitch.

**Build the cache file Friday night** when the first successful Graphiti dry run happens. Saving the working query result as JSON at that moment costs 10 minutes and saves the demo if Saturday afternoon goes sideways. Do not defer this to Sunday morning.

### 12.2 Other risks, ordered by impact

| Risk | Mitigation |
|---|---|
| Demo laptop loses wifi mid-demo | Browser auto-reconnects (one connection only). Have a mobile hotspot as backup. Backup video recorded Saturday night. |
| The team's server itself goes down | Have ssh access from a teammate's laptop. Keep services in a tmux session that can be restarted in <30s. Practice the restart sequence Saturday evening. |
| LLM produces wrong German legal references | Pre-load the wiki with verified BGB / BetrKV / HKV citations. System prompt instructs to cite from the wiki, not from training |
| Anthropic API rate-limit or outage during pitch | Have a second API key ready (different org); have the backup video ready |
| Team builds Graphiti perfectly but agent loop is broken | Friday-night vertical slice rule. If the agent is not calling Graphiti by Sat morning, that's a fire |
| Streamlit re-runs the page on every interaction and breaks the trace state | Use `st.session_state` for trace; serialize the session log to Postgres so reloads recover |
| One person becomes the bottleneck on Graphiti | Lead 1 documents commands as they go; Lead 2 must be able to take over by Sat noon |
| Enrichment payload doesn't validate against schema | Pydantic models with strict validation; system prompt includes the schema; pre-test with hardcoded inputs |
| Phone mockup looks fake / amateur | Spend time on CSS; reference real WhatsApp Web screenshots |
| Conflicts with existing app schema in Postgres | Use the `theo` schema exclusively. Coordinate Friday morning with whoever owns the existing schema. |
| Public exposure of in-progress server | All ports bound to `127.0.0.1`. Demo via SSH tunnel or auth'd reverse proxy. No `0.0.0.0` binds. |

---

## 13. The pitch integration

The pitch has a "what the product looks like" arc that runs through it:

1. Problem — the five complaints from `01_kundenkomplaints_mapping.md`
2. **The intake gap** — every PM gets WhatsApps, emails, calls, but none of it connects to operational data
3. **The product** — inbox-style ops platform with built-in enrichment
4. **Demo** (live)
5. **The reasoning under the hood** — Graphiti + temporal memory (this is where engineers in the audience lean in)
6. The five complaints + how we address each (the marktforschung mapping)
7. The autonomy spectrum
8. The roadmap (WEG, voicemail-to-text, owner reporting, etc.)
9. The ask

The pitch deck must include the customer-complaint mapping from `01_kundenkomplaints_mapping.md` as one of its slides. That is the strategic anchor and the reason a hallo theo audience cannot dismiss the project as "we already have AI."

Every demo moment maps to a pitch slide:

| Demo moment | Pitch slide it supports |
|---|---|
| Frau Köhler's WhatsApp arriving | "Tenants reach us through their channels, not our portal" |
| The inbox view | "Familiar UI, no learning curve for hallo theo's team" |
| Enrichment cards populating | "Every ticket arrives already understood" |
| Pattern card + timeline | "Temporal memory — the moat" |
| Jonas pre-approval card | "Reasoning across systems (chat, tickets, contracts)" |
| Sarah approves & sends | "Human in the loop — teammate, not autopilot" |
| WhatsApp reply going back out | "Closed loop — tenant gets their answer in minutes" |
| (Mentioned) NK & FixDirekt tickets in queue | "Same product handles different ticket categories" |
| Autonomy spectrum slide | "Three modes: autonomous, collaborative, assisted" |

---

## 14. Repository structure

Theo Copilot lives in a subdirectory of the existing repo (or wherever the team decides). Suggested layout:

```
theo-copilot/                     # new subdirectory in existing repo
├── PRODUCT_SPEC.md               # this file
├── DEMO_SKRIPT_v2.md             # the demo script
├── README.md                     # how to run it
├── pyproject.toml
├── docker-compose.theo.yml       # append to or merge with existing compose
├── .env.example                  # ANTHROPIC_API_KEY, NEO4J_*, OPENAI_API_KEY
│
├── data/
│   ├── seed.py                   # loads hallotheo_demo/* into Postgres + Graphiti
│   └── hallotheo_demo/           # the existing dataset (symlinked or copied)
│
├── domain_wiki/                  # L1 — markdown files
│   ├── index.md
│   ├── policies/
│   ├── procedures/
│   └── templates/
│
├── infra/
│   ├── db.py                     # SQLAlchemy/asyncpg connection to Postgres (theo schema)
│   ├── graphiti_client.py        # wrapper, group_id helpers
│   └── migrations/
│       └── 001_theo_schema.sql   # the CREATE SCHEMA + CREATE TABLE statements
│
├── intake/                       # channel intake — FastAPI
│   ├── main.py                   # FastAPI app, /webhook/whatsapp endpoint
│   ├── intake_service.py         # tenant lookup, ticket creation, graphiti episode write
│   └── intent_classifier.py      # Sonnet-based fast intent classification
│
├── agent/
│   ├── enrichment_loop.py        # the structured-output enrichment agent
│   ├── prompts.py
│   ├── enrichment_schema.py      # Pydantic models for the typed enrichment payload
│   ├── tools/
│   │   ├── l1_wiki.py
│   │   ├── l2_state.py
│   │   ├── l3_memory.py
│   │   ├── messaging.py          # send_whatsapp_reply, send_email_reply
│   │   └── vendor.py             # dispatch_vendor, approve_offer
│   └── trace.py                  # session-log writer
│
├── app/                          # the Streamlit inbox
│   ├── main.py                   # main page
│   ├── inbox.py                  # left column (ticket list)
│   ├── ticket_detail.py          # center (conversation) + right (enrichment)
│   ├── enrichment_cards.py       # the typed cards renderer
│   ├── timeline_viz.py           # the Pattern card timeline
│   ├── whatsapp_mockup.py        # the phone-shaped demo intake
│   └── action_panel.py           # suggested actions + approve/send
│
└── scripts/
    ├── ingest_graphiti.py        # Friday-night episode ingestion
    ├── verify_queries.py         # confirms the demo queries return expected facts
    ├── kill_switch_cache.py      # pre-computes fallback results
    └── reset_demo_state.py       # truncate + re-seed between dry runs
```

---

## 15. Definition of done

- [ ] Neo4j running on the team's server, reachable from the agent via bolt://neo4j:7687
- [ ] Postgres `theo` schema created, all tables and indexes in place
- [ ] All 8 hero episodes ingested into Graphiti, all demo queries verified to return useful facts
- [ ] Postgres seeded from the dataset, all L2 tools return correct data
- [ ] Wiki has 6 files written in German, all referenced by demo workflows
- [ ] WhatsApp mockup renders, a hardcoded message can be "sent" and triggers the intake via FastAPI
- [ ] Intake creates a ticket, identifies the tenant by phone, writes a Graphiti episode
- [ ] Intent classifier correctly tags the Köhler message as "heating / urgent"
- [ ] Enrichment loop runs against the ticket and produces a structured payload covering all 6 cards
- [ ] Pattern card timeline visualization renders correctly with the 6 Köhler incidents
- [ ] Inbox UI shows the ticket list with new ticket at top + the pattern marker
- [ ] Ticket detail view renders the conversation, enrichment cards, and suggested actions
- [ ] Sarah can click "Approve & Send" on the WhatsApp reply, the message appears in the phone mockup as "sent"
- [ ] Vendor dispatch and offer approval execute (write to Postgres, log in ticket timeline)
- [ ] Demo laptop can reach the server via SSH tunnel or reverse proxy, end-to-end verified on at least one network
- [ ] One full demo dry run completed in under 5 minutes
- [ ] Backup video recorded
- [ ] Kill-switch cache populated and tested
- [ ] Pitch deck ready, 8-10 slides, rehearsed five times
- [ ] (Optional) The Demir/NK secondary ticket also runs end-to-end through the same UI

---

## 16. Decisions deliberately deferred

These are the items where we picked an answer for the hackathon that production would need to revisit. Mentioned here so the team can answer Q&A honestly.

- **Why a separate `theo` schema in the existing Postgres** — clean isolation from existing app. Production: integrated into the main schema with proper migrations.
- **Why no candidates table for L3** — pre-ingestion. Production: agent writes candidates, human reviews.
- **Why Opus and not a smaller model for enrichment** — quality at demo. Production: a tiered policy (Sonnet by default, Opus for reasoning-heavy paths). Sonnet already used for intent classification.
- **Why no auth / RBAC on the Streamlit app** — single demo user. Production: full SSO/role model integrated with the existing app's identity system. Reverse proxy could enforce auth in the meantime.
- **Why Streamlit** — speed of build. Production: embed in hallo theo's actual platform UI.
- **Why no observability / metrics** — none needed for one demo. Production: tracing every tool call, costs, latencies, accuracy.
- **Why one channel (WhatsApp)** — focused demo. Production: email, voicemail, portal, phone with transcription all converge on the same enrichment pipeline.
- **Why no real WhatsApp Business API integration** — risk management. Production: real WhatsApp Business Cloud API with approved message templates for proactive flows.

These are good Q&A bait — they show the team thought about production, not just the demo.

---

## 17. Why this framing wins

For the team's benefit when explaining the project externally:

1. **Judges grasp it instantly.** "It's a Front-style inbox for property managers with AI built in" → everyone gets it in 5 seconds.

2. **The end-to-end loop is visible.** Tenant types → operator sees → operator approves → tenant receives. That's a *product*, not a demo of a feature. Business viability judging rewards this enormously.

3. **The AI moat (Graphiti) appears inside a product surface, not as the product surface.** This is how production AI products actually work, and it reads as more mature than "look at our agent."

4. **The complaint mapping pitch still works perfectly.** Every complaint maps to a moment in the new flow: "auf E-Mails wird nicht reagiert" → ticket reply in <60s; "Nebenkostenabrechnung €317 too high" → the NK ticket variant; "Mängel ignoriert" → the Pattern card preventing chronic mishandling; "Belegeinsicht verweigert" → every enrichment card carries its source.

5. **The WhatsApp channel choice is on-brand for Berlin/Germany.** WhatsApp is the dominant tenant-to-PM channel in Germany under 60 and increasingly above 60. hallo theo's marketing emphasizes "schnelle Reaktion" — WhatsApp is where speed-of-reaction is most visible to customers.
