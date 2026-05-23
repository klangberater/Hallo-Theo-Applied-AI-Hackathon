"""Pydantic models for the EnrichmentPayload.

The agent's final tool-use turn must emit a JSON object matching
`EnrichmentPayload`. The Streamlit UI renders typed cards from it
directly — no free-form prose between agent and UI.

See: docs/PRODUCT_SPEC.md §6.1 + §7.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Card primitives — every card carries its source citation.
# ---------------------------------------------------------------------------


class SourceCitation(BaseModel):
    """Where a fact in an enrichment card came from."""
    kind: Literal["ticket", "lease", "invoice", "nka", "email", "chat",
                  "graphiti", "wiki", "weather", "vendor_offer", "stubbed"]
    id: str | None = None
    excerpt: str | None = Field(
        default=None,
        description="Short verbatim excerpt that grounds the claim.",
    )


class TenantCard(BaseModel):
    tenant_id: str
    name: str
    since: date | None = None
    warnings: list[str] = Field(
        default_factory=list,
        description="Short flags like 'mietpreisgebunden', 'medical addendum 18.05.2024', "
                    "'lawyer daughter'. Surface in the UI as warning chips.",
    )
    sources: list[SourceCitation] = Field(default_factory=list)


class UnitCard(BaseModel):
    unit_id: str
    label: str
    qm: float | None = None
    lease_status: str | None = None
    rent_cold: float | None = None
    sources: list[SourceCitation] = Field(default_factory=list)


class TimelineEntry(BaseModel):
    """One dot on the Pattern timeline."""
    date: date
    fact: str
    source: SourceCitation


class PriorIncidentsCard(BaseModel):
    """The Pattern card — the Graphiti moment."""
    count: int
    timespan_months: int | None = None
    timeline: list[TimelineEntry] = Field(default_factory=list)
    pattern_summary: str = Field(
        description="One sentence: what the pattern reveals (e.g. 'Same root cause: "
                    "thermostat ventil, all unresolved.').",
    )
    source: Literal["graphiti", "postgres-fallback", "stubbed"] = "graphiti"


class VendorOfferCard(BaseModel):
    offer_id: str
    vendor_id: str
    vendor_name: str
    scope: str
    amount: float
    issued_at: date
    age_days: int
    status: str
    sources: list[SourceCitation] = Field(default_factory=list)


class ChatExcerpt(BaseModel):
    """Internal pre-approval surfacing — the Jonas moment."""
    sender: str
    sent_at: datetime
    body: str
    interpretation: str = Field(
        description="One line: why this matters for the current ticket "
                    "(e.g. 'Jonas pre-approved up to 500 EUR for vulnerable-tenant heating').",
    )
    source: SourceCitation


class WeatherCard(BaseModel):
    location: str
    forecast: str = Field(
        description="Free-text forecast summary (e.g. 'Frost Thu-Sun, -3°C nights')."
    )
    relevant_because: str
    source: SourceCitation = Field(
        default_factory=lambda: SourceCitation(kind="stubbed")
    )


class LegalRef(BaseModel):
    """A German legal reference. Pulled verbatim from the wiki — never invented."""
    citation: str = Field(description="e.g. 'BGB §535', 'BetrKV §7'")
    short_text: str
    relevance: str = Field(description="Why this applies to the current ticket.")
    source: SourceCitation


# ---------------------------------------------------------------------------
# Suggested action — proposed, not executed.
# ---------------------------------------------------------------------------


class SuggestedAction(BaseModel):
    action_type: Literal[
        "send_whatsapp_reply",
        "send_email_reply",
        "dispatch_vendor",
        "approve_offer",
        "request_invoice_itemization",
        "escalate_to_human",
    ]
    payload: dict = Field(
        description="Action-specific args (e.g. {thread_id, body} for send_whatsapp_reply)."
    )
    rationale: str = Field(
        description="One paragraph: why this action, citing source cards by reference."
    )
    source_citations: list[SourceCitation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    bundle_id: str | None = Field(
        default=None,
        description="When the action is part of a bundle_approve grouping, all actions "
                    "sharing the same bundle_id execute atomically on one approval. "
                    "None = standalone action.",
    )
    bundle_order: int = Field(
        default=0,
        description="Execution order within the bundle. send_whatsapp_reply / "
                    "send_email_reply MUST always be the highest (last) so a DB "
                    "rollback never strands an irreversible send.",
    )
    executed_at: str | None = Field(
        default=None,
        description="ISO timestamp if the action has already been executed "
                    "(autonomous_done mode). Null otherwise.",
    )


# ---------------------------------------------------------------------------
# Top-level payload — what the agent emits at end_turn.
# ---------------------------------------------------------------------------


class EnrichmentPayload(BaseModel):
    """The structured artifact that drives the ticket detail UI.

    The agent's final assistant message MUST be a JSON object validating
    against this schema. No prose outside the JSON. The Streamlit UI maps
    each field to a card renderer in `app/enrichment_cards.py`.
    """
    tenant_card: TenantCard
    unit_card: UnitCard
    lease_facts: list[str] = Field(
        default_factory=list,
        description="Short German excerpts from the lease that matter here.",
    )
    prior_incidents: PriorIncidentsCard
    open_vendor_offers: list[VendorOfferCard] = Field(default_factory=list)
    internal_pre_approvals: list[ChatExcerpt] = Field(default_factory=list)
    weather: WeatherCard | None = None
    legal_context: list[LegalRef] = Field(default_factory=list)
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)

    # ---- Autonomy ---------------------------------------------------------

    autonomy_mode: Literal["autonomous_done", "bundle_approve", "propose"] = Field(
        default="propose",
        description=(
            "How much agency Theo claims for this ticket.\n"
            "- 'autonomous_done': all actions already executed; trace visible. "
            "Allowed ONLY if every action has cost=0 (or covered by a standing "
            "pre-approval), no vulnerable-tenant flags, no legal history, and "
            "category precedent exists.\n"
            "- 'bundle_approve': Sarah approves once, all actions execute "
            "atomically. Use when actions are coherent and pre-approval covers "
            "any cost.\n"
            "- 'propose': default; each action approved individually."
        ),
    )
    autonomy_rationale: str = Field(
        default="",
        description="One paragraph explaining the autonomy_mode choice — which "
                    "guardrails fired (or didn't). Shown to Sarah as audit trail.",
    )


# Convenience: generate the JSON schema once — used in the system prompt so
# the model knows the exact shape it needs to emit.
def enrichment_payload_schema_json() -> dict:
    return EnrichmentPayload.model_json_schema()
