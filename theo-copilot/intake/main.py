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
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

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
    """Flat post-call payload — what handle_inbound() needs.

    Two ways to arrive here:
      (a) Real ElevenLabs post-call webhook — the nested envelope is
          normalised into this flat shape by _normalize_voicecall_payload.
      (b) Direct curl smoke test — caller posts this shape verbatim.

    Tenant lookup only needs `from_phone` + a body; everything else is
    metadata.
    """
    from_phone: str = Field(alias="from", description="Caller E.164 phone")
    transcript: str = Field(default="", description="Full call transcript")
    summary: str | None = Field(default=None, description="LLM summary of the call (preferred as body)")
    duration_seconds: int | None = None
    call_started_at: datetime | None = None
    conversation_id: str | None = None

    class Config:
        populate_by_name = True


def _normalize_voicecall_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Translate the ElevenLabs post-call envelope into our flat shape.

    The real ElevenLabs post-call webhook looks like:
      {
        "type": "post_call_transcription",
        "event_timestamp": ...,
        "data": {
          "agent_id": ..., "conversation_id": ...,
          "transcript": [{"role": "agent"/"user", "message": ..., ...}, ...],
          "metadata": {"call_duration_secs": ..., "start_time_unix_secs": ...},
          "analysis": {"transcript_summary": ..., "call_successful": ...},
          "conversation_initiation_client_data": {
            "dynamic_variables": {"caller_phone": "+49..."}
          }
        }
      }

    For browser-based web calls (the demo flow) there is no real caller-ID,
    so the page passes `caller_phone` as a dynamic variable when starting
    the conversation and we lift it out here.

    For curl smoke tests the payload is already flat — pass through.
    """
    if raw.get("type") == "post_call_transcription" or (
        isinstance(raw.get("data"), dict) and "conversation_id" in raw["data"]
    ):
        d = raw.get("data", {}) or {}
        analysis = d.get("analysis") or {}
        metadata = d.get("metadata") or {}
        cic = d.get("conversation_initiation_client_data") or {}
        dyn = cic.get("dynamic_variables") or {}

        turns = d.get("transcript") or []
        # User-only transcript is the right "body" for tenant intake — the
        # agent's prompts are scaffolding, not content. Fall back to the
        # full back-and-forth if the user said nothing intelligible.
        user_only = "\n".join(
            (t.get("message") or "").strip()
            for t in turns
            if (t.get("role") or "").lower() == "user" and (t.get("message") or "").strip()
        )
        full = "\n".join(
            f"{(t.get('role') or '?').upper()}: {(t.get('message') or '').strip()}"
            for t in turns
            if (t.get("message") or "").strip()
        )

        start_secs = metadata.get("start_time_unix_secs")
        call_started_at = (
            datetime.fromtimestamp(start_secs, tz=timezone.utc).isoformat()
            if isinstance(start_secs, (int, float)) and start_secs > 0 else None
        )

        return {
            "from": dyn.get("caller_phone") or dyn.get("from_phone") or "",
            "transcript": user_only or full,
            "summary": analysis.get("transcript_summary"),
            "duration_seconds": (
                int(metadata.get("call_duration_secs"))
                if isinstance(metadata.get("call_duration_secs"), (int, float))
                else None
            ),
            "call_started_at": call_started_at,
            "conversation_id": d.get("conversation_id"),
        }

    return raw  # already flat (e.g. curl smoke test)


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
        raw_dict = json.loads(raw_body.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"invalid JSON: {e}") from e

    # Translate ElevenLabs' nested post-call envelope into our flat shape.
    # Curl smoke tests sending the flat shape directly pass through unchanged.
    flat = _normalize_voicecall_payload(raw_dict)

    try:
        payload = VoiceCallPayload.model_validate(flat)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"invalid payload: {e}") from e

    if not payload.from_phone.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "missing caller_phone — the web widget must pass it as a "
                "dynamic variable, or a real telephony provider must "
                "supply the caller's E.164 number."
            ),
        )

    # Prefer the raw user-only transcript over ElevenLabs' summary. The
    # summary is heavily sanitised + often translated into English, which
    # destroys emergency-detection cues ("frost angekündigt", "Hüft-OP",
    # "schon wieder") that drive the urgency classifier. We append the
    # summary as supplemental context so the enrichment agent still has
    # the structured signal, but the verbatim user words come first.
    parts: list[str] = []
    if payload.transcript and payload.transcript.strip():
        parts.append(payload.transcript.strip())
    if payload.summary and payload.summary.strip():
        parts.append(f"[Zusammenfassung des Anrufs]\n{payload.summary.strip()}")
    body = "\n\n".join(parts).strip()
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
