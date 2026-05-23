# Claude AI Assistant Guidelines — Hallo Theo

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

❌ **DON'T**
- Auto-deploy to production.
- Skip lint/type checks.
- Commit secrets (.env, credentials) — verify `git status` first.
- Add backwards-compat shims for code that has no callers yet.
- Bury LLM prompts inside API handlers — keep them in `application/`.
