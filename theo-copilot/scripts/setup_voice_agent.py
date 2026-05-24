"""One-shot configurator for the Fletcher ElevenLabs voice agent.

Creates (or updates) a Conversational AI agent in your ElevenLabs
workspace that is configured as a 'polite recorder' for German tenant
voicemails. On hang-up, ElevenLabs POSTs the transcript + LLM summary
to /webhook/voicecall and Fletcher creates a ticket.

Usage:
    export ELEVENLABS_API_KEY=...
    python -m scripts.setup_voice_agent

Optional env overrides:
    FLETCHER_AGENT_NAME      — agent name (default: "Fletcher Voicemail Intake")
    FLETCHER_AGENT_ID        — update this specific existing agent (skips lookup)
    FLETCHER_VOICE_ID        — ElevenLabs voice ID (default: a multilingual voice)
    FLETCHER_WEBHOOK_URL     — post-call webhook (default: https://getfletcher.ai/api/webhook/voicecall)
    FLETCHER_MODEL           — TTS model id (default: eleven_flash_v2_5)
    FLETCHER_LLM             — LLM for the conversation (default: gemini-2.5-flash)

The script is idempotent: re-runs update the existing agent rather than
creating duplicates. Lookup is by exact name match.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Best-effort .env load (matches the rest of the codebase).
for _candidate in [
    Path("/opt/fletcher/.env"),
    Path(__file__).resolve().parent.parent / ".env",
    Path.cwd() / ".env",
]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break


API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
if not API_KEY:
    print("ERROR: ELEVENLABS_API_KEY not set in env.", file=sys.stderr)
    sys.exit(1)

AGENT_NAME = os.environ.get("FLETCHER_AGENT_NAME", "Fletcher Voicemail Intake")
AGENT_ID = os.environ.get("FLETCHER_AGENT_ID", "").strip() or None
# Default voice: "Sarah" — one of the stock voices that ships in every
# workspace ("Mature, Reassuring, Confident, professional"). Paired with
# eleven_flash_v2_5 she speaks German fluently with a mild non-native
# accent. Override via FLETCHER_VOICE_ID if you have a German-native
# voice in your workspace.
VOICE_ID = os.environ.get("FLETCHER_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
WEBHOOK_URL = os.environ.get(
    "FLETCHER_WEBHOOK_URL", "https://getfletcher.ai/api/webhook/voicecall",
)
MODEL = os.environ.get("FLETCHER_MODEL", "eleven_flash_v2_5")
LLM = os.environ.get("FLETCHER_LLM", "gemini-2.5-flash")

BASE = "https://api.elevenlabs.io"
HEADERS = {"xi-api-key": API_KEY, "Content-Type": "application/json"}

FIRST_MESSAGE = (
    "Hallo, hier ist die Telefon-Annahme von hallo theo. "
    "Bitte schildern Sie Ihr Anliegen — wir hören zu und melden uns "
    "anschließend bei Ihnen zurück."
)

SYSTEM_PROMPT = (
    "Du bist die automatische Telefon-Annahme einer deutschen Hausverwaltung "
    "(hallo theo). Der Anrufer ist ein Mieter und möchte ein Anliegen melden. "
    "Verhalte dich wie ein höflicher, geduldiger Anrufbeantworter mit "
    "Rückfrage-Fähigkeit.\n\n"
    "REGELN (strikt einhalten):\n"
    "- Sprich ausschließlich Deutsch, in der Sie-Form, ruhig und freundlich.\n"
    "- Höre den Mieter ausreden. Wenn das Anliegen unklar oder unvollständig "
    "ist, stelle EINE kurze Rückfrage (z.B. 'Welche Wohnung betrifft das?' "
    "oder 'Seit wann besteht das Problem?').\n"
    "- Wiederhole zum Abschluss kurz in EINEM Satz, was du verstanden hast.\n"
    "- Versprich KEINE konkreten Zeiten ('heute noch', 'in einer Stunde', "
    "'sofort'). Sag stattdessen: 'Ein Kollege meldet sich bei Ihnen.'\n"
    "- Nenne KEINE Paragraphen, KEINE Gesetze, KEINE Lösungsschritte. Du "
    "nimmst nur auf — die Bearbeitung erfolgt anschließend.\n"
    "- Wenn der Mieter angibt, es sei ein Notfall (Wasserschaden, kompletter "
    "Heizungsausfall im Winter, vulnerable Person), sage einmal: "
    "'Verstanden, wir behandeln das mit höchster Priorität.'\n"
    "- Beende das Gespräch mit: 'Vielen Dank für Ihre Nachricht, wir melden "
    "uns bei Ihnen. Auf Wiederhören.'"
)


def _request(method: str, path: str, **kw) -> dict:
    url = f"{BASE}{path}"
    r = httpx.request(method, url, headers=HEADERS, timeout=30.0, **kw)
    if r.status_code >= 400:
        raise SystemExit(
            f"ElevenLabs API {method} {path} → {r.status_code}\n{r.text[:1000]}"
        )
    return r.json() if r.text else {}


def _find_agent_by_name(name: str) -> str | None:
    data = _request("GET", "/v1/convai/agents")
    for a in data.get("agents", []):
        if a.get("name") == name:
            return a.get("agent_id")
    return None


# The Conversational AI agent config shape. Kept minimal — only the
# fields we actively care about. Anything we don't set inherits the
# workspace default. See: https://elevenlabs.io/docs/conversational-ai
def _agent_config() -> dict:
    return {
        "name": AGENT_NAME,
        "conversation_config": {
            "agent": {
                "first_message": FIRST_MESSAGE,
                "language": "de",
                "prompt": {
                    "prompt": SYSTEM_PROMPT,
                    "llm": LLM,
                    "temperature": 0.3,
                },
            },
            "tts": {
                "voice_id": VOICE_ID,
                "model_id": MODEL,
                "stability": 0.5,
                "similarity_boost": 0.7,
            },
            "asr": {
                "quality": "high",
                "user_input_audio_format": "pcm_16000",
            },
            "turn": {
                "turn_timeout": 8,
                "mode": "turn",
            },
        },
        "platform_settings": {
            "workspace_overrides": {
                # If a post-call webhook is set workspace-wide it fires
                # for this agent. We rely on that — the post_call webhook
                # is configured at workspace level, not per-agent.
            },
        },
    }


def main() -> None:
    agent_id = AGENT_ID
    if not agent_id:
        print(f"Looking up existing agent by name: {AGENT_NAME!r}…")
        agent_id = _find_agent_by_name(AGENT_NAME)

    cfg = _agent_config()

    if agent_id:
        print(f"Updating agent {agent_id}…")
        _request("PATCH", f"/v1/convai/agents/{agent_id}", json=cfg)
    else:
        print("Creating new agent…")
        result = _request("POST", "/v1/convai/agents/create", json=cfg)
        agent_id = result.get("agent_id") or result.get("id")
        if not agent_id:
            raise SystemExit(f"agent create returned no id:\n{json.dumps(result, indent=2)}")

    # Confirm by reading it back
    agent = _request("GET", f"/v1/convai/agents/{agent_id}")
    print()
    print(f"✓ Agent ready: {agent_id}")
    print(f"  Name:      {agent.get('name')}")
    cc = agent.get("conversation_config", {})
    print(f"  Language:  {cc.get('agent', {}).get('language')}")
    print(f"  Voice:     {cc.get('tts', {}).get('voice_id')}")
    print(f"  Model:     {cc.get('tts', {}).get('model_id')}")
    print(f"  LLM:       {cc.get('agent', {}).get('prompt', {}).get('llm')}")
    print()
    print("Dashboard:")
    print(f"  https://elevenlabs.io/app/conversational-ai/agents/{agent_id}")
    print()
    print("Manual steps still needed in the dashboard:")
    print("  1. Workspace → Webhooks → set Post-Call Webhook URL:")
    print(f"       {WEBHOOK_URL}")
    print("     and copy the HMAC secret into /opt/fletcher/.env as")
    print("     ELEVENLABS_WEBHOOK_SECRET=<secret>")
    print("  2. Workspace → Phone Numbers → buy/import a number and link")
    print(f"     it to this agent ({agent_id}).")
    print("  3. Place a test call from a seeded tenant's phone number")
    print("     (Köhler is +491793960546 in our seed).")
    print()


if __name__ == "__main__":
    main()
