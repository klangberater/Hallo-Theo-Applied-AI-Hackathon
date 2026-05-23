# Theo Copilot — L1 Domain Wiki

Stable domain facts the agent retrieves at enrichment time. Used by `agent/tools/l1_wiki.py`.

All content in German where it would be in production. See PRODUCT_SPEC §6.4.

## Files to write (Saturday morning per PRODUCT_SPEC §10)

- `policies/heating-emergency-de.md` — Heizperiode, BGB §535/536, response times
- `policies/mietminderung-handling-de.md` — how to evaluate and respond
- `policies/vendor-payment-rules.md` — itemization requirements, when to escalate
- `procedures/nka-defense-de.md` — how to defend a Nebenkostenabrechnung
- `procedures/vendor-anomaly-de.md` — template for requesting itemization
- `templates/tenant-acknowledgment-de.md`
- `templates/vendor-dispatch-de.md`

Each ~200 words. **Never invent legal citations** — pull verbatim from BGB / BetrKV / HKV.
