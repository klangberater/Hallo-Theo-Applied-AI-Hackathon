# Hallo Theo

An AI copilot for property management — built at the Applied AI Hackathon.

Hallo Theo reads from your property management system, channel managers, calendars, and messages, then helps you handle the operational work: drafting guest replies, scheduling tasks, and surfacing what needs attention.

## Docs

- **[CLAUDE.md](./CLAUDE.md)** — engineering guide for Claude Code assistants
- **[AGENTS.md](./AGENTS.md)** — workflow rules, repo conventions, deploy/test discipline
- **[docs/SPEC.md](./docs/SPEC.md)** — product behavior (source of truth)
- **[docs/architecture.md](./docs/architecture.md)** — system architecture + data model

## Stack

- **Backend**: FastAPI, Python 3.11+, asyncpg, Pydantic v2
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Storage**: PostgreSQL 14+ (with pgvector for embeddings)
- **LLM**: Anthropic Claude
- **Chat surfaces**: WhatsApp (Twilio), Slack (Bolt)

## Status

Pre-implementation — repo scaffolding only. See `docs/SPEC.md` to define what we're building.
