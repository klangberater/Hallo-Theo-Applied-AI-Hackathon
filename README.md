# Fletcher — AI Operations Inbox for German Property Management

> Built at the **Applied AI Hackathon** (May 23–25, 2026) for **hallo theo**, a digital Hausverwaltung administering Berlin WEGs (Wohnungseigentümergemeinschaften).
>
> **Live demo:** [getfletcher.ai](https://getfletcher.ai) · **Inbox:** [getfletcher.ai/inbox](https://getfletcher.ai/inbox)

Fletcher (codename: *Theo Copilot*) is an AI copilot that triages tenant messages from WhatsApp / email / voicemail, enriches each ticket with the full context a property manager needs — tenant history, lease, recurring patterns, vendor options, relevant legal/policy snippets — and then **either acts autonomously, proposes a one-click action bundle, or drafts a reply for review**, depending on a per-ticket policy.

The differentiator is a **temporal knowledge graph** (Graphiti + Neo4j) sitting alongside Postgres and a markdown wiki. The agent reasons over *facts that change over time* — "the Köhler heating has failed three winters running, escalating each time" — not just the current row in a table.

---

## Table of contents

1. [What it does](#what-it-does)
2. [Architecture](#architecture)
3. [Stack](#stack)
4. [Quick start (local dev)](#quick-start-local-dev)
5. [Deployment (production / demo server)](#deployment-production--demo-server)
6. [API reference](#api-reference)
7. [Agent tools (L1 / L2 / L3)](#agent-tools-l1--l2--l3)
8. [Autonomy modes](#autonomy-modes)
9. [Repository layout](#repository-layout)
10. [Demo flow for the jury](#demo-flow-for-the-jury)
11. [Documentation index](#documentation-index)
12. [Hackathon constraints & non-goals](#hackathon-constraints--non-goals)

---

## What it does

Within ~1–2 seconds of any inbound WhatsApp/email, the tenant gets an automatic German acknowledgement that references the topic of their message ("Vielen Dank für Ihre Nachricht. Es tut uns leid zu hören, dass Ihre Heizung wieder kalt ist — wir kümmern uns umgehend darum."). The full enrichment + agent response follows shortly after.

A property manager opens Fletcher and sees a single prioritised inbox of tenant tickets. For each ticket, Fletcher has already:

- **Classified intent + urgency** (DRINGEND / Wichtig / Standard) via Claude Sonnet
- **Looked up the tenant, unit, and active lease** in Postgres
- **Searched temporal memory** for recurring patterns ("3rd winter in a row")
- **Pulled relevant wiki snippets** (BGB §555c, BetrKV, internal policies)
- **Suggested concrete next actions** with German-language drafts ready to send

The manager either reviews and clicks "Aktionen umsetzen", or for low-risk routine work (annual chimney sweep coordination, etc.) finds the ticket already marked **Autonom erledigt** — Fletcher acted without intervention, with the full trace available for audit.

**Three real workflows are demoed end-to-end:**

1. **Köhler heating outage** — recurring pattern detected → bundle of 3 actions proposed (acknowledge tenant, dispatch Heizungsbau Walter, file BGB §555c notice)
2. **Demir noise complaint** — first-touch, propose mode → drafted neighbour mediation reply
3. **Schornsteinfeger annual sweep** — autonomous (already done by the time the manager opens the inbox)

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   WhatsApp   │     │    Email     │     │  Voicemail   │  (channels)
│  (Baileys)   │     │   (stub)     │     │   (stub)     │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌────────────────────────────────────────────────────────┐
│  FastAPI Intake (theo-copilot/intake/)                 │
│  • /webhook/whatsapp  → tenant lookup → ticket row     │
│  • Intent classifier (Claude Sonnet 4)                 │
│  • Immediate ack reply (Sonnet) → bridge /send         │
│  • Schedules background enrichment                     │
└────────────────────────┬───────────────────────────────┘
                         ▼
┌────────────────────────────────────────────────────────┐
│  Enrichment Agent (theo-copilot/agent/)                │
│  • Anthropic SDK tool-use loop (no LangChain)          │
│  • Claude Opus 4 with 17 tools across 3 memory layers  │
│  • Picks autonomy mode + writes EnrichmentPayload      │
│  • Captures full trace for jury audit                  │
└──────┬─────────────────┬─────────────────┬─────────────┘
       │ L1              │ L2              │ L3
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  Markdown    │  │ Postgres     │  │ Graphiti + Neo4j │
│  Wiki + BM25 │  │ (theo schema)│  │ (temporal facts) │
└──────────────┘  └──────────────┘  └──────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│  Next.js 15 Inbox (theo-copilot/frontend/)             │
│  • 3-column layout: list / detail / enrichment         │
│  • Per-ticket action panel (3 autonomy modes)          │
│  • Trace explorer for jury verification                │
└────────────────────────────────────────────────────────┘
```

**Full architecture document:** [docs/architecture.md](./docs/architecture.md)
**Product spec (source of truth):** [docs/PRODUCT_SPEC.md](./docs/PRODUCT_SPEC.md)
**Data-layer explainer (non-technical):** [docs/data-layers-overview.md](./docs/data-layers-overview.md)

---

## Stack

### Backend
| Component | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| Web framework | **FastAPI** 0.115+ | intake webhooks + read API for the frontend |
| Async DB driver | **asyncpg** 0.30+ | lenient JSONB codec (see `infra/db.py`) |
| Sync DB driver | psycopg2-binary | migrations + seed only |
| Validation | **Pydantic v2** | `EnrichmentPayload`, request/response models |
| Process manager | **systemd** | `fletcher-intake.service`, `fletcher-whatsapp.service` |

### LLM & Memory
| Component | Choice | Notes |
|---|---|---|
| Reasoning model | **Anthropic Claude Opus 4** (`claude-opus-4-5`) | enrichment agent loop |
| Fast model | **Anthropic Claude Sonnet 4** (`claude-sonnet-4-6`) | intent classification |
| Agent loop | **Raw `anthropic` SDK** with tool use | no LangChain / CrewAI / LangGraph |
| Temporal knowledge graph | **graphiti-core** 0.6+ on **Neo4j 5.26** | the technical moat |
| Graphiti LLM | **Together AI** (OpenAI-compatible) — Llama 3.3 70B Instruct | via `OPENAI_BASE_URL=https://api.together.xyz/v1` |
| Graphiti embeddings | **Together AI** — `intfloat/multilingual-e5-large-instruct` | German-capable |
| Wiki retrieval (L1) | **rank-bm25** over markdown | no vector store needed at this corpus size |

### Frontend
| Component | Choice | Notes |
|---|---|---|
| Framework | **Next.js 15** (App Router, static export) | served from nginx under `/inbox/` |
| Language | TypeScript 5.7 (strict mode) | |
| Styling | **Tailwind CSS 3** | custom paper + teal palette |
| Typography | Geist (sans) + Fraunces (serif) + JetBrains Mono | |
| Icons | lucide-react | |
| Runtime | React 19 | |

### Data
| Component | Choice | Notes |
|---|---|---|
| Relational DB | **PostgreSQL 14+** with `pgvector`, `pg_trgm`, `citext` | isolated under the `theo` schema |
| Graph DB | **Neo4j 5.26** (Docker, ports `127.0.0.1` only) | with APOC plugins |
| Wiki | **Markdown files** under `theo-copilot/domain_wiki/` | versioned in git |

### Channels
| Component | Choice | Notes |
|---|---|---|
| WhatsApp | **Baileys** (`@whiskeysockets/baileys` 6.7+) on Node 20 | QR pairing at `/pair`, multi-device, self-chat supported |
| Email / Voicemail | Stubbed | inbound via REST seed, not a live provider |

### Infrastructure
| Component | Choice |
|---|---|
| Server | Single bare-metal at `87.106.213.53` |
| Reverse proxy | nginx (TLS via Let's Encrypt) |
| Container runtime | Docker (Neo4j only — Python + Node run on the host) |
| CI/CD | GitHub Actions self-hosted runner → `git pull` + service restart on every push to `main` |
| Domain | `getfletcher.ai` (Strato registrar) |

---

## Quick start (local dev)

```bash
# 1. Clone
git clone https://github.com/<org>/Hallo-Theo-Applied-AI-Hackathon.git
cd Hallo-Theo-Applied-AI-Hackathon/theo-copilot

# 2. Python env
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .

# 3. Bring up Neo4j (Docker required)
cp .env.example .env  # then fill in NEO4J_PASSWORD, ANTHROPIC_API_KEY, OPENAI_API_KEY
docker compose -f docker-compose.theo.yml up -d neo4j

# 4. Postgres: create database + apply schema
createdb -h 127.0.0.1 -p 5432 -U postgres fletcher
psql -h 127.0.0.1 -U postgres -d fletcher \
  -f infra/migrations/001_theo_schema.sql

# 5. Seed the demo dataset (Köhler / Demir / Schornsteinfeger + history)
python -m data.seed

# 6. Pre-ingest Graphiti episodes (one-time, ~2–5 min)
python -m scripts.ingest_graphiti

# 7. Start the intake API
uvicorn intake.main:app --host 127.0.0.1 --port 8002 --reload

# 8. Start the frontend (in another terminal)
cd frontend && npm install && npm run dev   # http://localhost:3000

# 9. (Optional) WhatsApp bridge
cd ../bridges/whatsapp && npm install && npm start
# Open http://localhost:3001/pair, scan QR with your phone
```

### Required environment variables

Copy `theo-copilot/.env.example` → `.env` (or `/opt/fletcher/.env` on the server) and fill in:

```bash
DATABASE_URL=postgresql://fletcher:<pw>@127.0.0.1:5432/fletcher

NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<set-at-startup>

ANTHROPIC_API_KEY=sk-ant-...               # Claude Opus + Sonnet
OPENAI_API_KEY=<together-ai-key>           # Graphiti LLM + embeddings
OPENAI_BASE_URL=https://api.together.xyz/v1

ANTHROPIC_MODEL_REASONING=claude-opus-4-5
ANTHROPIC_MODEL_FAST=claude-sonnet-4-6

GRAPHITI_LLM_MODEL=meta-llama/Llama-3.3-70B-Instruct-Turbo
GRAPHITI_EMBED_MODEL=intfloat/multilingual-e5-large-instruct
GRAPHITI_EMBED_DIM=1024

USE_LIVE_GRAPHITI=true                     # set false to use kill-switch cache

WHATSAPP_BRIDGE_URL=http://127.0.0.1:8003  # where intake POSTs outbound msgs
```

---

## Deployment (production / demo server)

The demo is auto-deployed on every push to `main` via a GitHub Actions self-hosted runner on `87.106.213.53`. See [.github/workflows/](./.github/workflows/) for the exact pipeline.

**Manual deploy / debug:**

```bash
ssh root@87.106.213.53
cd /opt/fletcher && git pull
sudo systemctl restart fletcher-intake
sudo systemctl restart fletcher-whatsapp

# Frontend rebuild
cd theo-copilot/frontend && npm ci && npm run build
# Static export lands in frontend/out/ — nginx serves it from /inbox/
```

**Service layout on the server:**

| systemd unit | Port | What |
|---|---|---|
| `fletcher-intake` | `127.0.0.1:8002` | FastAPI — webhooks + read API |
| `fletcher-whatsapp` | `127.0.0.1:3001` | Baileys bridge + `/pair` UI |
| `theo-neo4j` (Docker) | `127.0.0.1:7687`, `7474` | Neo4j 5.26 |
| `fletcher-db` (existing host Postgres) | `127.0.0.1:5433` | shared Postgres, `theo` schema isolated |

All ports bound to `127.0.0.1`. Public access is only via nginx + TLS at `getfletcher.ai`.

---

## API reference

The FastAPI app exposes two surfaces: **inbound webhooks** (channels post here) and a **read/action API** the Next.js inbox consumes. nginx strips the `/api/` prefix when proxying to `127.0.0.1:8002`.

### Inbound webhooks

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET` | `/health` | — | `{"status": "ok"}` |
| `POST` | `/webhook/whatsapp` | `{from: str, body: str, sent_at?: iso8601, external_thread_id?: str}` | `{status: "accepted", ticket_id, intent, priority}` |
| `POST` | `/webhook/email` | `{from_email, subject, body, sent_at?}` | same shape as WhatsApp |
| `POST` | `/tickets/{ticket_id}/enrich` | — | triggers re-enrichment for an existing ticket |

### Inbox read API (consumed by the frontend)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/tickets` | list, filtered to status ≠ closed OR autonomy_mode = `autonomous_done`, sorted by priority then recency |
| `GET` | `/tickets/{id}` | full detail incl. enrichment payload + suggested actions |
| `GET` | `/tickets/{id}/trace` | every tool call the agent made — used in the right-pane trace explorer |
| `GET` | `/tickets/{id}/thread` | inbound + outbound channel messages |

### Action endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/tickets/{id}/actions/{idx}/execute` | execute a single suggested action (propose mode) |
| `POST` | `/tickets/{id}/bundle/execute` | execute all actions in the bundle (bundle_approve mode) |

### Demo controls (idempotent)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/demo/fire/koehler` | inject the Köhler heating ticket |
| `POST` | `/demo/fire/demir` | inject the Demir noise ticket |
| `POST` | `/demo/reset` | wipe state + re-seed; for the dry-run loop |

**OpenAPI:** the FastAPI app auto-generates schemas at `http://127.0.0.1:8002/docs` (Swagger UI) — disabled on the public domain.

---

## Agent tools (L1 / L2 / L3)

The enrichment agent (`agent/enrichment_loop.py`) is an Anthropic tool-use loop with **17 tools** spanning three memory layers. The model decides which to call based on the ticket.

### L1 — Domain wiki (markdown + BM25)

| Tool | Purpose |
|---|---|
| `search_wiki(query)` | BM25 over `domain_wiki/` |
| `read_wiki_page(path)` | full markdown of a page |

Wiki content covers: BGB / BetrKV / HKV citations · escalation procedures · tenant-reply templates · vendor onboarding rules.

### L2 — Operational state (Postgres `theo` schema)

| Tool | Purpose |
|---|---|
| `get_tenant`, `get_tenant_by_phone` | tenant row |
| `get_unit`, `get_lease` | unit + active lease |
| `list_tickets`, `get_ticket` | this tenant's ticket history |
| `list_invoices`, `get_nka` | invoices + annual operating-cost statement |
| `get_vendor`, `get_open_offers` | vendor directory + outstanding offers |
| `list_internal_chat` | colleague chat history about this tenant |

### L3 — Temporal memory (Graphiti + Neo4j) — the moat

| Tool | Purpose |
|---|---|
| `query_temporal_memory(query, entity_id?, valid_at?)` | semantic + temporal search across facts |
| `get_entity_timeline(entity_id)` | chronological fact history for a tenant / unit / vendor |

Episodes are pre-ingested by `scripts/ingest_graphiti.py` from the dataset; the agent reads only during demo runs.

### Action tools (proposers, not executors)

| Tool | Purpose |
|---|---|
| `messaging.send_whatsapp_reply` | drafts a reply (never auto-sends without operator approval) |
| `messaging.send_email_reply` | same, for email |
| `vendor.dispatch_vendor` | drafts a vendor dispatch |
| `vendor.approve_offer` | proposes accepting an open offer |
| `get_weather_forecast` | stubbed; logs "stubbed" in trace |

**Guardrail:** action tools write to Postgres and queue outbound messages but never hit a real provider during the demo. Outbound WhatsApp via Baileys is only enabled for explicit jury-shown moments.

---

## Autonomy modes

Every ticket gets one of three modes, decided by the agent based on confidence + risk + policy:

| Mode | UI label | Behaviour |
|---|---|---|
| `propose` | (no banner; action cards rendered individually) | Manager reviews each suggested reply / vendor dispatch and clicks individually. Default. |
| `bundle_approve` | "Bestätigen" chip | Manager sees a single "Aktionen umsetzen" button that executes 2–5 actions atomically. Used when actions are coherent. |
| `autonomous_done` | "Autonom" chip + green banner | Agent has already executed the actions. Trace is shown for audit. Used only for low-risk routine work (annual sweeps, document acknowledgements). |

Mode is selected by the model and stored on `theo.tickets.autonomy_mode`. The UI then renders one of three branches in `frontend/components/action-panel.tsx`.

---

## Repository layout

```
hallo-theo-applied-ai-hackathon/
├── README.md                       # this file
├── CLAUDE.md                       # AI assistant engineering guide
├── AGENTS.md                       # workflow rules, deploy discipline
├── docs/
│   ├── PRODUCT_SPEC.md             # 58k — source of truth
│   ├── architecture.md             # system diagrams + data flow
│   ├── data-layers-overview.md     # non-technical L1/L2/L3 explainer
│   └── fletcher-design-system.html # interactive style guide
├── landing/                        # static landing site at getfletcher.ai
├── tasks/                          # implementation plan + retro notes
└── theo-copilot/
    ├── data/
    │   ├── seed.py                 # loads dataset → Postgres
    │   └── hallotheo_demo/         # READ-ONLY source dataset
    ├── domain_wiki/                # L1 markdown wiki
    │   ├── policies/  procedures/  templates/
    ├── infra/
    │   ├── db.py                   # asyncpg pool + lenient JSONB codec
    │   ├── graphiti_client.py      # Together-AI-backed Graphiti wrapper
    │   └── migrations/001_theo_schema.sql
    ├── intake/                     # FastAPI
    │   ├── main.py                 # app + webhooks
    │   ├── api_routes.py           # /tickets, /trace, /actions, /demo
    │   ├── intake_service.py       # tenant lookup → ticket pipeline
    │   └── intent_classifier.py    # Claude Sonnet classifier
    ├── agent/
    │   ├── enrichment_loop.py      # Anthropic tool-use loop (no framework)
    │   ├── enrichment_schema.py    # Pydantic EnrichmentPayload
    │   ├── prompts.py              # system prompts + renderers
    │   ├── trace.py                # session-log writer
    │   └── tools/                  # l1_wiki, l2_state, l3_memory, messaging, vendor
    ├── frontend/                   # Next.js 15 inbox
    │   ├── app/                    # App Router pages
    │   ├── components/             # InboxList, TicketView, ActionPanel, EnrichmentCards
    │   └── lib/api.ts              # typed fetcher
    ├── bridges/whatsapp/           # Baileys bridge (Node 20)
    │   ├── index.js                # QR pairing + inbound → POST /webhook/whatsapp
    │   └── pair.html               # browser-side QR view
    ├── scripts/
    │   ├── ingest_graphiti.py      # pre-ingests episodes Friday night
    │   ├── kill_switch_cache.py    # pre-computes L3 fallback results
    │   ├── reset_demo_state.py     # truncate + re-seed between dry runs
    │   └── verify_queries.py       # sanity-check demo queries
    ├── docker-compose.theo.yml     # Neo4j 5.26
    ├── pyproject.toml
    └── .env.example
```

---

## Demo flow for the jury

A reproducible 3-minute walkthrough that exercises every layer:

1. **Open** [getfletcher.ai/inbox](https://getfletcher.ai/inbox). Three tickets visible in priority order.
2. **Köhler (DRINGEND, top of list)** — click row.
   - Right pane shows: tenant + unit + lease, recurring-pattern badge (🔁 3 — three winters), wiki snippet (BGB §555c), suggested vendor (Heizungsbau Walter).
   - Click **"Aktionen umsetzen"** — three actions execute, ticket closes, outbound WhatsApp drafted.
   - Click the **trace tab** — see every L1/L2/L3 tool call the agent made.
3. **Demir (Wichtig)** — click row.
   - Propose mode: individual reply card. Click **"Senden"** on the drafted neighbour-mediation message.
4. **Schornsteinfeger (Autonom)** — click row.
   - Green "Autonom erledigt" banner. Conversation thread shows the outbound message the agent already sent. Trace tab shows the autonomous reasoning.
5. **Reset for next jury** — `POST /api/demo/reset` (or the "Demo-Steuerung" expander).

**Backup path if Graphiti misbehaves:** flip `USE_LIVE_GRAPHITI=false` in `.env`. L3 falls back to a pre-computed JSON cache (`scripts/kill_switch_cache.py`); the demo continues with identical UI.

---

## Documentation index

| Doc | Audience | Purpose |
|---|---|---|
| **[docs/PRODUCT_SPEC.md](./docs/PRODUCT_SPEC.md)** | engineering | source of truth — read before changing anything in `theo-copilot/` |
| **[docs/architecture.md](./docs/architecture.md)** | engineering | system architecture + data model |
| **[docs/data-layers-overview.md](./docs/data-layers-overview.md)** | non-technical / jury | how L1 / L2 / L3 memory works, in plain language |
| **[docs/SPEC.md](./docs/SPEC.md)** | engineering | (legacy pre-hackathon product behaviour spec) |
| **[CLAUDE.md](./CLAUDE.md)** | AI assistants | engineering guide, hackathon-mode rules, things-to-never-do |
| **[AGENTS.md](./AGENTS.md)** | engineering | workflow rules, deploy/test discipline |
| **[tasks/todo.md](./tasks/todo.md)** | engineering | live implementation plan |
| **[tasks/lessons.md](./tasks/lessons.md)** | engineering | accumulated debugging lessons |
| **[theo-copilot/README.md](./theo-copilot/README.md)** | engineering | hackathon quickstart (server-focused) |

---

## Hackathon constraints & non-goals

This is a 48-hour build. We made explicit trade-offs that a production system would not:

- **No tests** unless they directly de-risk the demo path. Code quality is "would a senior reviewer let this through?" not "is it covered?"
- **No multi-tenancy.** Single hallo theo deployment, single property portfolio.
- **No real outbound sends to vendors / lawyers.** Action tools write drafts to Postgres; nothing leaves the box without explicit operator click.
- **No agent writes to Graphiti during demo sessions.** Episodes are pre-ingested Friday night; reads only at runtime.
- **No SaaS lock-in.** Anthropic + Together AI + self-hosted Neo4j + self-hosted Postgres. Switching providers is a config change.
- **No invented legal citations.** If the source isn't in the wiki or dataset, the agent says so. See the "Things to never do" section in [CLAUDE.md](./CLAUDE.md).

**What we'd build next** (post-hackathon, in priority order): real outbound providers (Twilio/Postmark), per-portfolio multi-tenancy, RBAC for the inbox, audit-log retention policy, agent eval harness, finer-grained autonomy policy per intent category.

---

## License

Proprietary — built for hallo theo. All rights reserved.

## Contact

Built by the Fletcher team at the Applied AI Hackathon, May 2026.
