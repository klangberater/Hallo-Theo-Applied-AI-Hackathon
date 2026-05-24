"""FastAPI intake — webhook endpoint + enrichment trigger.

POST /webhook/whatsapp     — accept inbound WhatsApp message, create ticket
POST /webhook/email        — same shape for email-originated tickets
POST /webhook/voicecall    — accept post-call data from ElevenLabs (transcript + summary)
POST /tickets/{id}/enrich  — manually trigger enrichment (idempotent)
GET  /health               — readiness check

Bind to 127.0.0.1:8002. nginx reverse-proxies /api/* → here.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from agent.enrichment_loop import enrich_ticket
from infra.db import close_pool, get_pool
from intake.api_routes import router as api_router
from intake.intake_service import handle_inbound

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("intake")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()  # warm the pool
    yield
    await close_pool()


app = FastAPI(title="Theo Copilot Intake", lifespan=lifespan)
app.include_router(api_router)


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


class VoiceCallPayload(BaseModel):
    """Post-call payload from ElevenLabs Conversational AI.

    We accept ElevenLabs' native field names where convenient and a few
    short aliases. The tenant lookup only needs `from_phone` + a body;
    everything else is metadata.
    """
    from_phone: str = Field(alias="from", description="Caller E.164 phone")
    transcript: str = Field(default="", description="Full call transcript")
    summary: str | None = Field(default=None, description="LLM summary of the call (preferred as body)")
    duration_seconds: int | None = None
    call_started_at: datetime | None = None
    conversation_id: str | None = None

    class Config:
        populate_by_name = True


# ---------------------------------------------------------------------------
# ElevenLabs webhook HMAC verification
# ---------------------------------------------------------------------------

ELEVENLABS_WEBHOOK_SECRET = os.environ.get("ELEVENLABS_WEBHOOK_SECRET", "").strip()
if not ELEVENLABS_WEBHOOK_SECRET:
    log.warning(
        "ELEVENLABS_WEBHOOK_SECRET not set — /webhook/voicecall will accept "
        "unsigned requests. Fine for local dev, NOT fine for production."
    )


def _verify_elevenlabs_signature(raw_body: bytes, signature_header: str | None) -> None:
    """Verify the ElevenLabs post-call webhook signature.

    Format ElevenLabs sends: `t=<unix_ts>,v0=<hex_sig>` where the signed
    payload is `{timestamp}.{raw_body}` and the HMAC algorithm is SHA-256.

    If ELEVENLABS_WEBHOOK_SECRET is unset, we skip verification entirely
    (dev-friendly). If it IS set, we require a valid header — missing or
    malformed signatures get 401.
    """
    if not ELEVENLABS_WEBHOOK_SECRET:
        return  # opt-in via env

    if not signature_header:
        raise HTTPException(status_code=401, detail="missing signature header")

    # Parse "t=...,v0=..." format. Tolerant of extra fields / ordering.
    parts = {}
    for chunk in signature_header.split(","):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            parts[k.strip()] = v.strip()

    timestamp = parts.get("t")
    given_sig = parts.get("v0")
    if not timestamp or not given_sig:
        raise HTTPException(status_code=401, detail="malformed signature header")

    signed_payload = f"{timestamp}.{raw_body.decode('utf-8', errors='replace')}"
    expected = hmac.new(
        ELEVENLABS_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, given_sig):
        raise HTTPException(status_code=401, detail="invalid signature")


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


@app.post("/webhook/voicecall")
async def webhook_voicecall(
    request: Request,
    background: BackgroundTasks,
    elevenlabs_signature: str | None = Header(default=None, alias="ElevenLabs-Signature"),
) -> dict:
    """Post-call webhook from ElevenLabs Conversational AI.

    Routes the call (caller phone + transcript/summary) into the standard
    intake pipeline with channel='voicemail'. Same ticket creation, intent
    classification, enrichment loop — only the channel and the body source
    differ. No realtime reply is sent (the call is already over); the
    DB-only ack channel_message just records that the system received the
    voicemail.
    """
    raw_body = await request.body()
    _verify_elevenlabs_signature(raw_body, elevenlabs_signature)

    try:
        payload = VoiceCallPayload.model_validate_json(raw_body)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"invalid payload: {e}") from e

    # Prefer the LLM-generated summary — it's cleaner for downstream
    # classification + enrichment than a raw transcript with ums/ahs. Fall
    # back to the transcript if no summary was sent.
    body = (payload.summary or payload.transcript or "").strip()
    if not body:
        raise HTTPException(status_code=422, detail="empty transcript and summary")

    # Each call becomes its own thread — calls don't have the same
    # "same-day continuity" assumption that WhatsApp / email do.
    ext_id = f"call_{payload.conversation_id}" if payload.conversation_id else None

    result = await handle_inbound(
        channel="voicemail",
        from_phone=payload.from_phone,
        body=body,
        sent_at=payload.call_started_at,
        external_thread_id=ext_id,
    )
    if result["status"] != "accepted":
        raise HTTPException(status_code=422, detail=result)

    background.add_task(_run_enrichment, result["ticket_id"])
    log.info(
        "voicecall accepted: ticket=%s from=%s duration=%ss conv=%s",
        result["ticket_id"], payload.from_phone,
        payload.duration_seconds, payload.conversation_id,
    )
    return result


@app.post("/tickets/{ticket_id}/enrich")
async def manual_enrich(ticket_id: str) -> dict:
    """Re-run enrichment for an existing ticket. Useful for dry runs."""
    asyncio.create_task(_run_enrichment(ticket_id))
    return {"ticket_id": ticket_id, "status": "enrichment_scheduled"}
