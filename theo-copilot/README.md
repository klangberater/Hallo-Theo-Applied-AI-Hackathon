# Theo Copilot

AI-powered operations inbox for hallo theo. 48-hour hackathon build.

> **Spec:** `../docs/PRODUCT_SPEC.md` is the source of truth. Read it before changing anything here.
> **Plan:** `../tasks/todo.md` is the live implementation plan.
> **Mode:** `../CLAUDE.md` — see "Theo Copilot — Hackathon Mode" at the top.

---

## Layout (per PRODUCT_SPEC §14)

```
theo-copilot/
├── data/
│   ├── seed.py                       # loads hallotheo_demo/ → Postgres
│   └── hallotheo_demo/               # source dataset (do NOT modify)
├── domain_wiki/                      # L1 — markdown files
│   ├── policies/
│   ├── procedures/
│   └── templates/
├── infra/
│   ├── db.py                         # asyncpg/SQLAlchemy connection to theo schema
│   ├── graphiti_client.py            # graphiti-core wrapper + group_id helpers
│   └── migrations/
│       └── 001_theo_schema.sql       # CREATE SCHEMA + tables from §6.1
├── intake/                           # FastAPI
│   ├── main.py                       # /webhook/whatsapp endpoint
│   ├── intake_service.py             # tenant lookup, ticket creation, episode write
│   └── intent_classifier.py          # Sonnet-class fast classifier
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
├── app/                              # Streamlit inbox
│   ├── main.py
│   ├── inbox.py
│   ├── ticket_detail.py
│   ├── enrichment_cards.py
│   ├── timeline_viz.py
│   ├── whatsapp_mockup.py
│   └── action_panel.py
├── scripts/
│   ├── ingest_graphiti.py            # Friday-night episode ingestion
│   ├── verify_queries.py             # confirms demo queries return expected facts
│   ├── kill_switch_cache.py          # pre-computes fallback results (§12.1)
│   └── reset_demo_state.py           # truncate + re-seed between dry runs
├── docker-compose.theo.yml           # Neo4j 5.26 service
├── pyproject.toml
└── .env.example
```

---

## Quick start (Friday evening)

### 1. On the server (87.106.213.53)

```bash
# Pull the latest main
cd /opt/fletcher && git pull   # or wherever the repo gets checked out

# Bring up Neo4j
docker compose -f theo-copilot/docker-compose.theo.yml up -d neo4j

# Apply the theo schema
docker exec -i fletcher-db psql -U fletcher -d fletcher \
  < theo-copilot/infra/migrations/001_theo_schema.sql
```

### 2. Local Python env (per-lead, each lead's own machine OR a shared tmux on server)

```bash
cd theo-copilot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Required env vars in `/opt/fletcher/.env`

| Var | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | Lead 3 (data + intake), Lead 2 (agent L2 tools) | already set; fletcher-db on :5433 |
| `NEO4J_URI` | Lead 1, Lead 2 | `bolt://127.0.0.1:7687` |
| `NEO4J_PASSWORD` | Lead 1, Lead 2 | TBD |
| `OPENAI_API_KEY` | Lead 1 | Graphiti uses OpenAI for fact extraction by default |
| `ANTHROPIC_API_KEY` | Lead 2 | intent classifier (Sonnet) + enrichment loop (Opus) |

### 4. Smoke test

After Friday-night hello-worlds:

```bash
# Lead 1
python -m theo_copilot.scripts.ingest_graphiti --episode heating-incident-2024-10
python -m theo_copilot.agent.tools.l3_memory --query "Köhler heating issues"

# Lead 3
curl -X POST http://127.0.0.1:8002/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"from": "+491701234567", "body": "Die Heizung im Wohnzimmer ist wieder kalt."}'

# Lead 4 (Streamlit)
streamlit run theo-copilot/app/main.py --server.port 8501 --server.address 127.0.0.1
```

### 5. Demo access

SSH tunnel from demo laptop:

```bash
ssh -L 8501:127.0.0.1:8501 root@87.106.213.53
# Then open http://localhost:8501 in the demo browser
```

---

## Build order

See `../tasks/todo.md` — Phase 1 (Friday eve) through Phase 6 (Sunday afternoon pitch).

**Rule:** the vertical-slice rule from PRODUCT_SPEC §10 wins. If Lead 1's Graphiti hello-world isn't returning real temporal facts by Saturday noon, drop everything else and fix it.

## Things to never do

See `../CLAUDE.md` → "Theo Copilot — Hackathon Mode" → "Things to never do".
