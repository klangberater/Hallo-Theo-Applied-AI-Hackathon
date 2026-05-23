"""Vendor action tools.

dispatch_vendor(vendor_id, scope, urgency) — creates a theo.vendor_dispatches row.
approve_offer(offer_id) — updates theo.vendor_offers.status='approved'.

Gated by UI approval like messaging tools.

Owner: Lead 2. PRODUCT_SPEC §5.4.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
