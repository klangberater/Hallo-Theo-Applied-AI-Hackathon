"""FastAPI intake — webhook endpoint + enrichment trigger.

POST /webhook/whatsapp     — accept inbound WhatsApp message, create ticket
POST /webhook/email        — same shape for email-originated tickets
POST /tickets/{id}/enrich  — manually trigger enrichment (idempotent)
GET  /health               — readiness check

Bind to 127.0.0.1:8002. nginx reverse-proxies /api/* → here.
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.enrichment_loop import enrich_ticket
from infra.db import close_pool, get_pool
from intake.intake_service import handle_inbound

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("intake")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()  # warm the pool
    yield
    await close_pool()


app = FastAPI(title="Theo Copilot Intake", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class WhatsAppPayload(BaseModel):
    from_: str = Field(alias="from", description="E.164 phone number")
    body: str
    sent_at: datetime | None = None
    external_thread_id: str | None = None

    class Config:
        populate_by_name = True


class EmailPayload(BaseModel):
    from_address: str
    body: str
    subject: str | None = None
    sent_at: datetime | None = None
    external_thread_id: str | None = None


# ---------------------------------------------------------------------------
# Background enrichment runner
# ---------------------------------------------------------------------------


async def _run_enrichment(ticket_id: str) -> None:
    """Fire-and-forget enrichment. Errors are logged, not propagated."""
    try:
        log.info("starting enrichment for %s", ticket_id)
        await enrich_ticket(ticket_id)
        log.info("enrichment complete for %s", ticket_id)
    except Exception as e:  # noqa: BLE001
        log.exception("enrichment failed for %s: %s", ticket_id, e)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "theo-intake",
            "now": datetime.now(timezone.utc).isoformat()}


@app.post("/webhook/whatsapp")
async def webhook_whatsapp(
    payload: WhatsAppPayload, background: BackgroundTasks,
) -> dict:
    result = await handle_inbound(
        channel="whatsapp",
        from_phone=payload.from_,
        body=payload.body,
        sent_at=payload.sent_at,
        external_thread_id=payload.external_thread_id,
    )
    if result["status"] != "accepted":
        raise HTTPException(status_code=422, detail=result)

    background.add_task(_run_enrichment, result["ticket_id"])
    return result


@app.post("/webhook/email")
async def webhook_email(
    payload: EmailPayload, background: BackgroundTasks,
) -> dict:
    result = await handle_inbound(
        channel="email",
        from_email=payload.from_address,
        body=payload.body,
        sent_at=payload.sent_at,
        external_thread_id=payload.external_thread_id,
    )
    if result["status"] != "accepted":
        raise HTTPException(status_code=422, detail=result)

    background.add_task(_run_enrichment, result["ticket_id"])
    return result


@app.post("/tickets/{ticket_id}/enrich")
async def manual_enrich(ticket_id: str) -> dict:
    """Re-run enrichment for an existing ticket. Useful for dry runs."""
    asyncio.create_task(_run_enrichment(ticket_id))
    return {"ticket_id": ticket_id, "status": "enrichment_scheduled"}
