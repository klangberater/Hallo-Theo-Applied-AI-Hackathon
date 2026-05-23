"""Outbound messaging tools.

send_whatsapp_reply(thread_id, body) — INSERTs theo.channel_messages with direction='outbound'. The WhatsApp mockup UI polls and renders it. Never hits a real WhatsApp API.

send_email_reply(thread_id, subject, body) — same pattern for email.

These tools are gated by Sarah's 'Approve & Send' click in the UI — the agent prepares proposals; the UI executes.

Owner: Lead 2. PRODUCT_SPEC §5.4.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
