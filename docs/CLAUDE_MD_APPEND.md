# CLAUDE.md — Section to Append

> **Instructions for the team:** Paste the content below into your existing `CLAUDE.md` as a new top-level section, near the top (before any existing project-specific guidance, since this is time-bounded work that overrides normal patterns). Once the hackathon is over, you can remove this section or migrate the parts you want to keep.

---

# === BEGIN APPEND ===

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

### How to interact with the human

This team is in a hackathon. Be terse. Show your work but not your reasoning at length. If you'd ask 3 clarifying questions, ask 1 and ship a default for the other 2.

# === END APPEND ===
