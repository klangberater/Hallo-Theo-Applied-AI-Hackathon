# Agent Guidelines — Hallo Theo

## Product Behavior Source of Truth

`docs/SPEC.md` is the canonical source of truth for product behavior across web and chat surfaces.

- If behavior in code or another doc conflicts with the spec, follow `docs/SPEC.md` unless the user explicitly says otherwise.
- Keep `AGENTS.md` focused on agent workflow, repo conventions, and engineering guidance.
- Do not add new product behavior rules here — put them in `docs/SPEC.md`.

## Mandatory: Clarify Surface for Bug Reports

When the user reports a bug without specifying the surface (web frontend, WhatsApp bot, Slack bot, or backend API), **always ask which surface** before investigating. Each has independent code paths.

## Mandatory: Restart Dev Servers After Backend Changes

Whenever you modify any Python file under `src/`, restart the dev servers so the running backend picks up your changes:

```bash
./scripts/stop.sh && ./scripts/start.sh
```

The backend does NOT hot-reload. If you skip this, the user will hit stale code and see confusing errors.

## Mandatory: Keep Architecture Diagram Up to Date

When you make architectural changes (new API endpoints, new services, new storage tables, new real-time flows, new external integrations, or major frontend restructuring), update `docs/architecture.md`. The file contains Mermaid diagrams that render on GitHub — keep them accurate.

## Mandatory: Work Directly on Main

All work happens directly on `main`. Commit and push after every completed work item.

- **Always push immediately after every commit.** Do not wait for the user to ask.
- After each completed work item, state explicitly in the final reply whether you committed and pushed (include the commit SHA), or say "not committed" / "not pushed" otherwise.

## Mandatory: Use Test Credentials for Browser Preview

When verifying web changes in a browser preview, sign in with the registered test account rather than stopping at the login screen. Credentials live in `.env.claude-test` (`CLAUDE_TEST_EMAIL` / `CLAUDE_TEST_PASSWORD`). Read the file directly — do not hard-code.

## LLM Discipline

Hallo Theo is LLM-driven. A few non-negotiables:

- **Prompts live in `src/halloteo/llm/prompts/`** — never inline a multi-paragraph prompt inside an API handler.
- **Every tool the model can call has a unit test** that exercises the tool's pure logic without the LLM. The LLM is not the integration test.
- **Always pass a system prompt.** Never rely on the default model behavior.
- **Cost discipline:** prefer Haiku-class models for classification / routing tasks, Sonnet for reasoning, Opus only when the user explicitly needs it.
- **No secrets in prompts.** PII (guest names, addresses) must be scrubbed from logged prompts.

## Testing

- New backend logic ships with pytest tests. Run `PYTHONPATH=src python3 -m pytest tests/ -v` before committing anything non-trivial.
- LLM-touching changes ship with at least one eval input in `evals/` — even a single case is better than zero.
- Frontend changes ship with at minimum a typecheck pass (`npx tsc --noEmit`) and a manual browse-check.

## Code Style

- Python: ruff (format + check) is the only formatter. 88-char lines. Docstrings on public functions.
- TypeScript: ESLint + Prettier. Strict TS mode. No `any` without a justification comment.
- No emojis in code unless the user explicitly asks.
- No clever one-liners when a clear three-liner exists.
- Comments explain **why**, not **what**. If the code is self-explanatory, no comment.

## Deployment

> Hackathon mode — deployment is **manual** until further notice.

- Deployment scripts live in `scripts/deploy.sh` (TBD).
- ✅ Always ask the user for permission before deploying.
- ✅ Run tests + lint before deploying.
- ✅ Verify locally first.
- ❌ No auto-deploy on push to main during the hackathon.

## Project Management

For the hackathon, track work in `tasks/todo.md`. After completing a task:
- Mark it done.
- If the user corrected you, capture the lesson in `tasks/lessons.md`.

## When You're Stuck

- Read related code before guessing.
- For complex tasks (3+ steps or architectural decisions), enter plan mode and confirm with the user before implementing.
- If something goes sideways, stop and re-plan rather than pushing through.
