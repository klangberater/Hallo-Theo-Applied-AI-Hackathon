"""L2 state tools — Postgres queries against theo schema.

Implements every function listed in PRODUCT_SPEC §5.1:
- get_unit, get_tenant, get_tenant_by_phone, get_lease
- list_tickets, get_ticket, list_invoices, get_invoice, get_nka
- get_vendor, get_open_offers
- get_thread, list_internal_chat
- list_tickets_for_operator, get_ticket_with_enrichment
- get_weather_forecast (stub — hardcoded JSON; log 'stubbed' in trace per CLAUDE_MD_APPEND)

Owner: Lead 2 + Lead 3 collaboratively. PRODUCT_SPEC §5.1.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
