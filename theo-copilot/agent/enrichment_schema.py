"""Pydantic models for the typed enrichment payload.

EnrichmentPayload mirrors the JSON shape in PRODUCT_SPEC §6.1 (lines ~471-487):
- tenant_card: TenantCard
- unit_card: UnitCard
- lease_facts: list[str]
- prior_incidents: PriorIncidentsCard (count, timespan_months, timeline, pattern_summary, source)
- open_vendor_offers: list[VendorOffer]
- internal_pre_approvals: list[ChatExcerpt]
- weather: WeatherCard | None
- legal_context: list[LegalRef]

Plus SuggestedAction (action_type, payload, rationale, source_citations).

Strict validation — system prompt instructs the model to emit valid JSON matching this schema.

Owner: Lead 2. PRODUCT_SPEC §6.1 + §7.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
