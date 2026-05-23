# Theo Copilot — Implementation Plan

> **Source of truth:** `docs/PRODUCT_SPEC.md`. This file translates the spec's §10 build plan into a state-aware task list grounded in what already exists in this repo + on the team server. Read PRODUCT_SPEC §10 first; this is the operating doc, not the design doc.
>
> _Authored: 2026-05-23, before Friday-evening kickoff._

---

## 0. Review notes on PRODUCT_SPEC

The spec is solid and ready to execute against. Five risks/gotchas worth surfacing before kickoff:

1. **Graphiti needs an LLM for fact extraction.** Per the graphiti-core docs it defaults to OpenAI. The spec's `.env.example` lists `OPENAI_API_KEY` — make sure that key is real and funded, otherwise the moat (§2.1 L3) silently degrades. Anthropic is *not* the LLM Graphiti uses internally; we use Anthropic for the agent loop only.
2. **Anthropic model names** in the spec (`claude-opus-4-7`, `claude-sonnet-4-6`) may have shifted by hackathon day — confirm in `docs.claude.com` Friday morning. The spec acknowledges this in CLAUDE_MD_APPEND.
3. **Streamlit re-runs on every interaction** — flagged in §12.2. The reasoning trace state must live in `st.session_state` AND be serialized to Postgres so a re-run recovers. Easy to forget; bites hard mid-demo.
4. **Phone mockup as theater (§8 View 1)** — easy to under-invest in. Allocate a real person early; CSS phone-shape with two bubbles is enough but it has to look credible.
5. **Kill-switch cache (§12.1)** — spec is explicit: build it Friday night when the first real Graphiti query works. Do NOT defer to Sunday. Ten minutes Friday, demo-saver Saturday.

One gap not addressed in the spec: **the dataset is referenced as already existing** (`theo-copilot/data/hallotheo_demo/`) but isn't checked into this repo. P0 to source it Friday morning.

---

## 1. Current state — what we already have

### Repo
- `CLAUDE.md` updated with the hackathon-mode override section (this commit)
- `AGENTS.md`, `docs/architecture.md`, `docs/SPEC.md` — pre-hackathon scaffolding, lower priority but kept
- `docs/PRODUCT_SPEC.md`, `docs/CLAUDE_MD_APPEND.md` — the new authoritative spec
- `landing/` — static landing page at https://getfletcher.ai
- `.github/workflows/deploy-landing.yml` — auto-rsync on push to `main` (touched `landing/**`)
- `.gitignore` covers `.env`, `.venv`, `__pycache__`, `.lean-ctx`, etc.

### Server (87.106.213.53, Ubuntu 24.04)
- nginx + Let's Encrypt for `getfletcher.ai` + `www`, HTTP→HTTPS redirect on
- nginx vhost already reverse-proxies `/api/` → `127.0.0.1:8002` and `/ws` upgrade — that port is free and earmarked for the FastAPI intake (was originally Fletcher's, repurpose for theo-intake)
- `fletcher-db` Docker container: `pgvector/pgvector:pg16` on `127.0.0.1:5433`, extensions `vector / citext / pg_trgm` enabled, password in `/opt/fletcher/.env` (chmod 600, github-runner)
- `cockpit-db-1` (postgres 16-alpine on :5432, owned by another project) — **do not touch**
- `nebula@blue` running on :8000 — **do not touch**
- `fletcher.service` systemd unit installed (disabled, placeholder)
- `/opt/fletcher/{backend,frontend/dist,logs}` directory layout
- self-hosted github-actions runners at `/opt/actions-runner*` (registered to nebula repo, not this one — informational only)
- certbot 2.9.0, scheduled renewals
- 348G disk (90% free), 11G RAM (8G available), Docker running

### Repo secrets
- `DEPLOY_SSH_KEY` — ed25519 deploy key for landing-page rsync, lives in `github-runner` user's authorized_keys

---

## 2. What's missing — must land before Friday 19:00

Ordered by criticality. Each blocks at least one Friday-evening lead.

| # | Item | Owner | Blocks |
|---|---|---|---|
| 1 | `theo-copilot/data/hallotheo_demo/` dataset checked in | TBD | Lead 1, 2, 3, 4 |
| 2 | `ANTHROPIC_API_KEY` in `/opt/fletcher/.env` | TBD | Lead 1, 2 |
| 3 | `OPENAI_API_KEY` in `/opt/fletcher/.env` (Graphiti's extraction LLM) | TBD | Lead 1 |
| 4 | `theo-copilot/` directory tree scaffolded per §14 (empty files OK) | Claude | Lead 1, 2, 3, 4 |
| 5 | Lead assignments confirmed in writing | Alex | n/a |
| 6 | `docker-compose.theo.yml` with Neo4j 5.26 service drafted | Lead 1 | Lead 1 |
| 7 | `infra/migrations/001_theo_schema.sql` drafted | Lead 3 | Lead 3 |

---

## 3. Decisions to lock Friday morning

These are decisions where I've already taken a default — flagged as `[default]` — but each is worth a 60-second team confirmation before kickoff:

1. **Postgres host: `fletcher-db` on 127.0.0.1:5433** `[default]`.
   - Rationale: already provisioned, isolated, has pgvector (unused but free), no risk of stepping on `cockpit-db-1` or any other app's data.
   - Connection string fragments already in `/opt/fletcher/.env`: `DB_HOST=127.0.0.1`, `DB_PORT=5433`, `DB_USER=fletcher`, `DB_PASSWORD=...`, `DATABASE_URL=...`.
   - Action: create `CREATE SCHEMA IF NOT EXISTS theo;` inside the `fletcher` database. All theo tables go there. Do NOT reuse the existing `cockpit` schema's tables — the spec's "reuse existing app tables" guidance assumes a property-mgmt app already exists here; it doesn't.

2. **Demo access: SSH tunnel as primary** `[default]`, per spec §9.3 Option A.
   - Alternative: `theo.getfletcher.ai` via nginx + HTTP Basic Auth. Costs ~15 min Friday to set up if the team prefers a public URL.
   - Action item: confirm with the team which laptop runs the demo; pre-share that user's SSH pubkey on the server.

3. **Branch / CI strategy: work on `main`, no CI for theo-copilot/ yet** `[default]`.
   - Each lead pushes incremental commits straight to `main`. No tests = no PR gate to fail.
   - The existing `deploy-landing.yml` workflow only triggers on `landing/**` changes, so theo work won't accidentally redeploy landing.
   - **Risk:** main breaks for everyone if someone pushes garbage. Mitigation: be careful, push small commits, lean on `git revert` if needed.

4. **Reverse-proxy port mapping**:
   - nginx already forwards `getfletcher.ai/api/` → `127.0.0.1:8002`. Use `:8002` for the FastAPI intake service (theo-intake) as the spec implies (different from spec's `:8000` to avoid clashing with Nebula's `:8000`).
   - Streamlit on `:8501` (spec default). nginx will need an additional location block if we go public-URL route (location `/` → `127.0.0.1:8501` upgrade). For SSH-tunnel demo, no nginx change needed.

5. **Anthropic model choice for the demo**:
   - Intent classifier: latest Haiku-class or Sonnet-class fast model.
   - Enrichment loop: latest Opus-class reasoning model.
   - Confirm exact identifiers Friday morning — spec names may be stale.

---

## 4. Phase plan (mapped to PRODUCT_SPEC §10)

### Phase 1 — Friday evening, 19:00–23:00 (4 hours)

Four parallel vertical slices. Each lead ships a hello-world by 23:00. **Strict rule:** no integration work tonight; just prove each slice's atomic capability.

#### Lead 1 — Graphiti / Neo4j (the moat)
- [ ] `docker-compose.theo.yml`: add `neo4j:5.26` service, bind `127.0.0.1:7687` + `127.0.0.1:7474`, password env, `apoc` plugin, `neo4j_data` volume
- [ ] `docker compose -f docker-compose.theo.yml up -d neo4j` on the server
- [ ] Browser-verify Neo4j UI at `http://localhost:7474` via SSH tunnel
- [ ] `theo-copilot/agent/infra/graphiti_client.py` — wrap `graphiti-core`, accept `OPENAI_API_KEY` for extraction
- [ ] Smoke test: add ONE Köhler episode (`heating-incident-2024-10` from §6.2), then run a query against `tenant:koehler_we4l` — confirm Graphiti extracts at least one fact
- [ ] Update `theo-copilot/README.md` with bolt URI, password, "how to nuke + reseed" instructions

#### Lead 2 — Enrichment agent skeleton
- [ ] `theo-copilot/agent/enrichment_schema.py` — Pydantic models for the `EnrichmentPayload` from §6.1 (tenant_card, unit_card, lease_facts, prior_incidents{count, timespan_months, timeline, pattern_summary, source}, open_vendor_offers, internal_pre_approvals, weather, legal_context)
- [ ] `theo-copilot/intake/intent_classifier.py` — Sonnet-class call, returns `{intent, urgency, confidence}` per §7.1
- [ ] `theo-copilot/agent/enrichment_loop.py` — full tool-use loop per §7.2 pseudocode. Tools start as stubs returning hardcoded JSON.
- [ ] `theo-copilot/agent/prompts.py` — system prompt per §7.3
- [ ] `theo-copilot/agent/trace.py` — append-only session log (writes to `theo.trace_events` table OR a file path; spec leaves either OK)
- [ ] Hello-world: hardcode the Köhler WhatsApp body, run the loop, get a valid `EnrichmentPayload` JSON back

#### Lead 3 — Data + intake
- [ ] `theo-copilot/infra/migrations/001_theo_schema.sql` — every `CREATE TABLE` from §6.1, all under `theo` schema, all indexes
- [ ] Apply migration: `docker exec -i fletcher-db psql -U fletcher -d fletcher < 001_theo_schema.sql` (or use a migration runner of choice)
- [ ] `theo-copilot/data/seed.py` — read `hallotheo_demo/` → insert into `theo.*` tables (idempotent: TRUNCATE first or `ON CONFLICT DO UPDATE`)
- [ ] `theo-copilot/intake/main.py` — FastAPI app, `POST /webhook/whatsapp` accepts a stub payload, looks up tenant by phone, creates a ticket row, fires off an episode to Graphiti, returns 200
- [ ] Hello-world: `curl POST /webhook/whatsapp` with the Köhler payload → ticket row exists in `theo.tickets` → episode written to Graphiti

#### Lead 4 — Streamlit inbox shell
- [ ] `theo-copilot/app/main.py` — Streamlit page, three columns layout
- [ ] `theo-copilot/app/inbox.py` — ticket list reading from `theo.tickets`
- [ ] `theo-copilot/app/ticket_detail.py` — conversation (left) + enrichment (right), reading from `tickets.enrichment` JSONB
- [ ] `theo-copilot/app/enrichment_cards.py` — one renderer per card type (TenantCard, UnitCard, PriorIncidentsCard, etc.)
- [ ] Hello-world: page renders with one hardcoded ticket + hardcoded enrichment JSON, looks structurally credible. Polish comes later.

#### 5th track (parallelizable, ~2h) — Phone-shaped WhatsApp mockup
- [ ] `theo-copilot/app/whatsapp_mockup.py` or `theo-copilot/app/static/phone.html`
- [ ] CSS phone-shape div with status bar, conversation list, two message bubbles
- [ ] Reference real WhatsApp Web screenshots for fidelity
- [ ] Timed JS reveal: bubbles appear typed-out over ~3s on demo trigger

### Phase 2 — Saturday morning, 08:00–13:00 (5 hours): wire it together

- [ ] **Lead 1:** ingest all 8 hero episodes from §6.2 via `scripts/ingest_graphiti.py`. For each, verify the temporal query returns useful facts. **Snapshot the working results as JSON for the kill-switch cache (§12.1).**
- [ ] **Lead 2:** swap all stubbed tools in the enrichment loop for real implementations:
  - [ ] `tools/l2_state.py` — Postgres queries (use SQLAlchemy or asyncpg, your call)
  - [ ] `tools/l1_wiki.py` — BM25 over markdown files (rank-bm25 lib is fine)
  - [ ] `tools/l3_memory.py` — Graphiti query wrapper
  - [ ] `tools/messaging.py`, `tools/vendor.py` — write to Postgres only, never external
- [ ] **Lead 3:** write the 6 wiki markdown files in German per §6.4:
  - `policies/heating-emergency-de.md`
  - `policies/mietminderung-handling-de.md`
  - `policies/vendor-payment-rules.md`
  - `procedures/nka-defense-de.md`
  - `procedures/vendor-anomaly-de.md`
  - `templates/tenant-acknowledgment-de.md` + `templates/vendor-dispatch-de.md`
- [ ] **Lead 3:** wire intake → enrichment trigger. After ticket row + Graphiti episode, fire async call to enrichment loop; persist payload back to `tickets.enrichment` + `tickets.suggested_actions`.
- [ ] **Lead 4:** wire inbox + detail to live Postgres data. Build the Pattern card timeline visualization (the Graphiti moment — invest CSS here).
- [ ] **All:** run the Köhler scenario end-to-end at least once. WhatsApp body in → enrichment cards render → suggested actions visible.

### Phase 3 — Saturday afternoon, 13:00–19:00 (6 hours): demo loop polish

- [ ] Stopwatched dry runs every 90 minutes (≈4 runs across the afternoon)
- [ ] After each dry run, fix the single worst thing observed
- [ ] If primary Köhler workflow is solid by 17:00, add the Demir/NK secondary ticket (§3.2)
- [ ] **Do NOT add new functionality after 18:00.** Lockdown begins at 19:00.

### Phase 4 — Saturday evening, 19:00–23:00 (4 hours): lockdown

- [ ] Polish trace UI, German copy, briefing format
- [ ] Record a backup video of the full demo, upload to a known URL
- [ ] Verify the kill-switch path: `USE_LIVE_GRAPHITI=False` → demo still runs from cache
- [ ] Test SSH tunnel from the actual demo laptop on actual demo wifi (or a comparable network)
- [ ] Backup mobile hotspot ready
- [ ] Practice the service restart sequence (Neo4j + theo-intake + theo-app) — should be <30s

### Phase 5 — Sunday morning, 08:00–11:30: pitch + final dry run

- [ ] Pitch deck per §13: problem → intake gap → product → demo → moat → complaint mapping → autonomy → roadmap → ask
- [ ] Five timed rehearsals
- [ ] Final dry run at 11:30 — whatever's broken at 11:30 we don't fix; we route around

### Phase 6 — Sunday afternoon: pitch

---

## 5. Coordination notes

- **Each lead pushes to `main` directly.** Small commits, descriptive messages, no PR review (no time). If you break someone's slice, fix it immediately or revert.
- **One tmux session on the server** runs all services + tails logs. Any team member can `ssh root@87.106.213.53` and see what's happening.
- **`scripts/reset_demo_state.py`** is essential — between dry runs, truncate `theo.*` tables, re-run seed, re-ingest Graphiti episodes. Each lead can call this without coordinating.
- **Anthropic spend** for one demo ≈ $3. Total for a weekend of dev + dry runs ≈ $50. Cap nothing yet, monitor for runaway loops.
- **Q&A bait** lives in PRODUCT_SPEC §16. Skim those before the pitch — judges who ask "why X" are testing whether you considered alternatives.

---

## 6. Definition of done

Pulled verbatim from PRODUCT_SPEC §15 — work this checklist when triaging "what's left":

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
