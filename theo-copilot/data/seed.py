"""Load hallotheo_demo/ into the theo Postgres schema.

Reads source files from data/hallotheo_demo/, parses each (emails as RFC 822-ish, mietverträge as text excerpts, NKA as structured prose), inserts into theo.tenants / theo.properties / theo.units / theo.leases / theo.tickets / theo.emails / theo.invoices / theo.nka. Idempotent: TRUNCATE theo.* tables first.

Owner: Lead 3 (Data + intake). PRODUCT_SPEC §10 Friday evening.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
