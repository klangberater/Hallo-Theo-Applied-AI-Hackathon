"""FastAPI app — channel intake webhook.

POST /webhook/whatsapp accepts {from, body, sent_at?, media?} and triggers intake_service.handle_inbound(). Bind to 127.0.0.1:8002 (nginx reverse-proxies /api/* → here).

Owner: Lead 3. PRODUCT_SPEC §10 Friday evening, §9.1.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
