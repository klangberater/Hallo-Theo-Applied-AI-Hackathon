# Claude AI Assistant Guidelines — Hallo Theo

## Theo Copilot — Hackathon Mode (May 23–25)

> This section overrides normal project conventions for the duration of the Theo Copilot hackathon. After Sunday, this section can be removed or migrated.

### Context

A team subset is building **Theo Copilot** — an AI-powered operations inbox for hallo theo — in this repo over 48 hours. Code lives under `theo-copilot/`. Full spec at `theo-copilot/PRODUCT_SPEC.md` — **read it before making non-trivial changes to anything in that directory.**

### Critical context

- **Time is the binding constraint.** If a clean approach takes 4 hours and a hacky one takes 1, default to the hacky one. We will not refactor.
- **Graphiti + Neo4j is the technical moat.** It must work end-to-end before any other work begins. If `theo-copilot/agent/tools/l3_memory.py` is not returning real temporal facts by Saturday noon, that's a fire.
- **The dataset already exists** at `theo-copilot/data/hallotheo_demo/`. Do not regenerate or modify it. Load it; trust it.
- **The agent uses Anthropic tool use directly.** No LangChain, no CrewAI, no LangGraph. Raw `anthropic` SDK with a tool-use loop. The spec explains why.
- **No tests** unless they're directly de-risking the demo path. We're not building a library.

### Stack (for the hackathon code only)

- Python 3.11+
- `anthropic` SDK (Anthropic models — use `claude-opus-4-7` for reasoning, `claude-sonnet-4-6` for routine tools / intent classification)
- `graphiti-core` + Neo4j 5.26 (via Docker on the team's server)
- **Postgres on the existing server**, isolated under the `theo` schema. Do not pollute the existing app's tables.
- Streamlit for the frontend
- FastAPI for the intake webhook
- Markdown files for the L1 wiki

### Database hygiene

- All Theo Copilot tables live under the Postgres `theo` schema. Migrations in `theo-copilot/infra/migrations/`.
- Use `SET search_path TO theo, public` in connections so the agent's L2 tools see Theo tables first.
- Do not modify any existing schema's tables. If we need data from them, read-only access via SQL — never `ALTER` or `INSERT`.

### Build order

The order in `theo-copilot/PRODUCT_SPEC.md` §10 is not a suggestion. Follow it:
1. Friday evening: 4 parallel vertical slices, each shipping a hello-world by 23:00
2. Saturday: wire them together, run all 4 workflows end-to-end
3. Saturday evening: lockdown, polish, record backup video, verify the kill-switch
4. Sunday morning: pitch deck and rehearsal

### When you don't know something

- For Graphiti API surface: check current docs at the graphiti-core PyPI page or its GitHub repo. The API has changed and may change again.
- For the Anthropic SDK: check https://docs.claude.com — model names and API surface may have moved since this spec was written.
- For German legal references (BGB, BetrKV, HKV): use what's in the dataset and the wiki. Do not invent citations. If something legally precise is needed and not in the data, ask the human.

### Things to never do (in the hackathon code)

- Never modify files under `theo-copilot/data/hallotheo_demo/` — that's the source of truth dataset.
- Never let the agent send a real email, make a real API call to a vendor, or take any action outside the local Postgres + Neo4j. The agent proposes; humans dispose.
- Never let the agent write to Graphiti during a demo session. Episodes are pre-ingested by `theo-copilot/scripts/ingest_graphiti.py` on Friday night. The agent reads only.
- Never invent legal citations. If you don't have a source, say so.
- Never use stub data without flagging it. If the weather tool is hardcoded JSON, log "stubbed" in the trace.
- Never bind a service to `0.0.0.0` in the docker-compose. All ports `127.0.0.1` only. Demo access via SSH tunnel or the existing reverse proxy.
- Never commit `.env` files or API keys. Standard discipline still applies even at hackathon speed.

### Keep the README current

The root `README.md` is the jury-facing document. **Update it as part of any change that affects what it claims** — new endpoint, new agent tool, new env var, new service, stack swap, architectural shift, demo-flow change. The README must always describe the system as it actually is, not as it was scaffolded. If you change behaviour and don't touch the README, you haven't finished the task.

Same rule for `theo-copilot/README.md` when the change is implementation-level (file layout, systemd units, smoke-test commands).

### How to interact with the human

This team is in a hackathon. Be terse. Show your work but not your reasoning at length. If you'd ask 3 clarifying questions, ask 1 and ship a default for the other 2.

---

## Pre-hackathon guidance (lower-priority — superseded by the section above for any conflict)

This document is the engineering guide for Claude AI assistants working on **Hallo Theo**, an AI copilot for property management. Pair it with:

- **[AGENTS.md](./AGENTS.md)** — workflow rules, repo conventions, deploy/test discipline.
- **[docs/SPEC.md](./docs/SPEC.md)** — product behavior (source of truth).
- **[docs/architecture.md](./docs/architecture.md)** — system architecture and data model.

If product behavior in code conflicts with `docs/SPEC.md`, follow `docs/SPEC.md` unless the user says otherwise.

## Quick Start

```bash
# Backend (FastAPI)
./scripts/start.sh       # start API + workers (TBD)
./scripts/stop.sh        # stop everything
tail -f backend.log

# Frontend (React + Vite)
cd frontend && npm run dev

# Tests
PYTHONPATH=src python3 -m pytest -v
cd frontend && npm run test
```

> Scripts marked TBD are placeholders — wire them up as the repo grows.

## Code Quality Standards

### Before Committing

```bash
# Python — format + lint (ruff)
python3 -m ruff format src/
python3 -m ruff check --fix src/

# Frontend — lint + types
cd frontend && npm run lint
cd frontend && npx tsc --noEmit

# Tests (only what's relevant to your change)
PYTHONPATH=src python3 -m pytest tests/<area>/ -v
```

- Python lines ≤ 88 chars. Break long f-strings across lines.
- Imports use parenthesized multiline form when > 88 chars.
- No emojis in code unless the user asks.
- TypeScript strict mode. No `any` without comment justification.

## Project Structure

```
hallo-theo/
├── src/halloteo/        # Backend Python code (FastAPI)
│   ├── api/             # FastAPI routes
│   ├── application/     # Use-case orchestration (LLM turns, RAG, integrations)
│   ├── storage/         # PostgreSQL access (asyncpg)
│   ├── llm/             # LLM client + prompt templates
│   ├── integrations/    # Property data sources (PMS, channel managers)
│   └── auth/            # Auth + sessions
├── frontend/            # React + TypeScript + Vite
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       └── lib/
├── bots/                # Chat surfaces (WhatsApp/Slack adapters)
├── tests/
├── docs/                # SPEC + architecture
└── scripts/             # Dev + deploy helpers
```

> Directory names are proposals — adjust as the implementation lands.

## Development Workflow

### 1. Making Changes
- Read related code before modifying. Match existing patterns.
- Write tests alongside non-trivial logic.
- Update `docs/SPEC.md` if you change product behavior.
- Update `docs/architecture.md` if you change system structure (new service, table, integration, real-time flow).
- **Update `README.md`** whenever the change affects anything it documents — endpoints, agent tools, env vars, stack, services, demo flow. The README is the jury/onboarding entry point; never let it drift.

### 2. Testing Locally
- Restart dev servers after backend changes — the backend does **not** hot-reload.
- For frontend, Vite hot-reloads automatically.
- For LLM-touching changes, run a small eval set before claiming "works".

### 3. Committing
- Work directly on `main`. No feature branches in hackathon mode.
- Commit + push after every completed work item — never batch.
- After each completed work item, explicitly state in the final reply whether you committed and pushed.

### 4. Deploying
- See [AGENTS.md](./AGENTS.md#deployment) for the deploy process.
- Never auto-deploy without user permission.

## Common Tasks

### Add a new API endpoint
1. Route in `src/halloteo/api/<module>.py`.
2. Pydantic request/response models.
3. Use-case logic in `src/halloteo/application/<module>/`.
4. Storage access in `src/halloteo/storage/`.
5. Tests in `tests/test_api_<module>.py`.
6. Frontend client + UI if user-facing.

### Add a new LLM tool / RAG source
1. Tool spec in `src/halloteo/application/copilot/tools/`.
2. Register in the tool registry.
3. Add an eval prompt to confirm the model picks it up correctly.

### Modify the database schema
1. Add a migration in `src/halloteo/storage/migrations/`.
2. Update storage helpers + DTOs.
3. Update tests.
4. Bump the schema version table.

### Add a new chat surface (WhatsApp / Slack)
1. Adapter under `bots/<surface>/`.
2. Map inbound events to a canonical `IncomingMessage`.
3. Route through the same application layer as the web client — never duplicate use-case logic.

## Key Technologies

- **Backend**: FastAPI, Python 3.11+, asyncpg, Pydantic v2
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Storage**: PostgreSQL 14+ (with `pgvector` for embeddings, `citext` for emails)
- **LLM**: Anthropic Claude (via official SDK) — see `docs/architecture.md` for routing
- **Chat surfaces**: WhatsApp (Baileys/Twilio TBD), Slack (Bolt SDK)
- **Auth**: JWT access + refresh, bcrypt password hashing

## Helpful Commands

```bash
# Find long Python lines
awk 'length > 88 {print NR": "length" chars"}' src/halloteo/api/copilot.py

# Run one test
PYTHONPATH=src python3 -m pytest tests/test_copilot.py::test_routing -v

# Build frontend
cd frontend && npm run build

# Type check frontend
cd frontend && npx tsc --noEmit
```

## Remember

✅ **DO**
- Read `docs/SPEC.md` before changing product behavior.
- Restart dev servers after backend changes.
- Run linters before committing.
- Write tests for new logic.
- Keep `docs/architecture.md` accurate.
- Keep `README.md` accurate — update it whenever you change anything it documents.

❌ **DON'T**
- Auto-deploy to production.
- Skip lint/type checks.
- Commit secrets (.env, credentials) — verify `git status` first.
- Add backwards-compat shims for code that has no callers yet.
- Bury LLM prompts inside API handlers — keep them in `application/`.
