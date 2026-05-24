# Theo Copilot — implementation

AI-powered operations inbox for hallo theo. The codebase under this directory.

> **Primary README** (jury-facing): see [`../README.md`](../README.md) at the repo root.
> **Product spec:** `../docs/PRODUCT_SPEC.md` is the source of truth. Read it before changing anything here.
> **Plan + retro:** `../tasks/todo.md`

---

## Layout

```
theo-copilot/
├── data/
│   ├── seed.py                       # loads hallotheo_demo/ → Postgres
│   └── hallotheo_demo/               # source dataset (do NOT modify)
├── domain_wiki/                      # L1 — markdown files
│   ├── policies/  procedures/  templates/
├── infra/
│   ├── db.py                         # asyncpg pool + lenient JSONB codec
│   ├── graphiti_client.py            # Together-AI-backed Graphiti wrapper
│   └── migrations/001_theo_schema.sql
├── intake/                           # FastAPI
│   ├── main.py                       # app + /webhook/whatsapp
│   ├── api_routes.py                 # /tickets, /trace, /actions, /demo
│   ├── intake_service.py             # tenant lookup → ticket pipeline
│   └── intent_classifier.py          # Claude Sonnet 4 classifier
├── agent/
│   ├── enrichment_loop.py            # Anthropic SDK tool-use loop
│   ├── enrichment_schema.py          # Pydantic EnrichmentPayload
│   ├── prompts.py
│   ├── trace.py                      # session-log writer
│   └── tools/
│       ├── l1_wiki.py                # BM25 over markdown
│       ├── l2_state.py               # Postgres queries
│       ├── l3_memory.py              # Graphiti queries (THE MOAT)
│       ├── messaging.py              # send_whatsapp_reply, send_email_reply
│       └── vendor.py                 # dispatch_vendor, approve_offer
├── frontend/                         # Next.js 15 inbox (App Router, static export)
│   ├── app/                          # pages
│   ├── components/                   # InboxList, TicketView, ActionPanel, EnrichmentCards
│   └── lib/api.ts                    # typed fetcher
├── bridges/whatsapp/                 # Baileys bridge (Node 20)
│   ├── index.js                      # inbound → POST /webhook/whatsapp; outbound via POST /send
│   └── pair.html                     # QR pairing page
├── scripts/
│   ├── ingest_graphiti.py            # Friday-night episode ingestion
│   ├── verify_queries.py             # confirms demo queries return expected facts
│   ├── kill_switch_cache.py          # pre-computes L3 fallback (§12.1)
│   └── reset_demo_state.py           # truncate + re-seed between dry runs
├── docker-compose.theo.yml           # Neo4j 5.26 service
├── pyproject.toml
└── .env.example
```

---

## Quick start (server, `87.106.213.53`)

```bash
# Pull the latest main
cd /opt/fletcher && git pull

# Bring up Neo4j
docker compose -f theo-copilot/docker-compose.theo.yml up -d neo4j

# Apply the theo schema (first time only)
psql -h 127.0.0.1 -p 5433 -U fletcher -d fletcher \
  < theo-copilot/infra/migrations/001_theo_schema.sql

# Seed the demo dataset
cd theo-copilot && python -m data.seed

# Pre-ingest Graphiti episodes
python -m scripts.ingest_graphiti

# Restart services
sudo systemctl restart theo-intake theo-whatsapp-bridge
```

## Quick start (local laptop)

See the [root README](../README.md#quick-start-local-dev) — that's the canonical local setup.

---

## Required env vars

Copy `.env.example` → `/opt/fletcher/.env` on the server (or `.env` locally) and fill in:

| Var | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | intake, agent | host Postgres, `theo` schema |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | graphiti_client | bolt to the local container |
| `ANTHROPIC_API_KEY` | agent + intent classifier | Claude Opus + Sonnet |
| `OPENAI_API_KEY` | graphiti_client | Together AI key (OpenAI-compatible) |
| `OPENAI_BASE_URL` | graphiti_client | `https://api.together.xyz/v1` |
| `GRAPHITI_LLM_MODEL` | graphiti_client | default: `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
| `GRAPHITI_EMBED_MODEL` | graphiti_client | default: `intfloat/multilingual-e5-large-instruct` |
| `USE_LIVE_GRAPHITI` | l3_memory tool | `false` flips to kill-switch cache |
| `WHATSAPP_BRIDGE_URL` | intake_service | where to POST outbound (default `http://127.0.0.1:8003`) |
| `ELEVENLABS_WEBHOOK_SECRET` | intake/main.py | shared HMAC secret for the `/webhook/voicecall` post-call signature. Unset = unsigned requests accepted (dev only). |

---

## Smoke tests

```bash
# Intake
curl -X POST http://127.0.0.1:8002/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"from": "+491701234567", "body": "Die Heizung ist wieder kalt."}'

# Read API
curl http://127.0.0.1:8002/tickets | jq '.[0]'

# L3 sanity check (returns real temporal facts about Köhler)
python -m scripts.verify_queries

# Frontend
cd frontend && npm run dev    # http://localhost:3000
```

---

## Demo access

The public demo is at [getfletcher.ai/inbox](https://getfletcher.ai/inbox) — nginx + TLS in front of the local services.

For deep-debug access (Neo4j browser, raw Postgres), SSH-tunnel:

```bash
ssh -L 7474:127.0.0.1:7474 -L 5433:127.0.0.1:5433 root@87.106.213.53
# Neo4j browser: http://localhost:7474
# Postgres: psql -h 127.0.0.1 -p 5433 -U fletcher fletcher
```

---

## Build order

See `../tasks/todo.md` — Phase 1 (Friday eve) through Phase 6 (Sunday afternoon pitch).

**Rule:** the vertical-slice rule from PRODUCT_SPEC §10 wins. If L3 (Graphiti) doesn't return real temporal facts, nothing else matters.

## Things to never do

See `../CLAUDE.md` → "Theo Copilot — Hackathon Mode" → "Things to never do".
