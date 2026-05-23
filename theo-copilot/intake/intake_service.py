"""Inbound message → ticket + episode pipeline.

1. Look up tenant by E.164 phone (theo.tenants)
2. Resolve unit + property
3. Create ticket row (status='open', classified_intent=None)
4. Run intent_classifier → set tickets.classified_intent + priority
5. Add episode to Graphiti (group_ids=[tenant:..., property:...])
6. Fire enrichment_loop.enrich_ticket(ticket_id) asynchronously
7. Update tickets.status='enriching' → 'ready_for_review'

Owner: Lead 3. PRODUCT_SPEC §3.1 Phase A + §7 flow diagram.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
