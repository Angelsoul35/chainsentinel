"""Write a suspicious-activity report (SAR) narrative for an alert.

Two modes: a deterministic template (no LLM) and an LLM-written narrative through
the provider cascade. The LLM only turns the signals into prose; the detection
and the score come from the rules and the model, and a human analyst reviews.
"""

from __future__ import annotations

from .llm import LLMClient, build_llm
from .schema import Alert

_SYSTEM = (
    "You are an AML analyst. Using ONLY the signals given, write a short, factual "
    "suspicious-activity report (100-150 words). Do not invent facts. Name the typologies, "
    "summarise the flow, and state that a human analyst must review before filing a SAR."
)


def template_report(alert: Alert) -> str:
    lines = [
        f"SUSPICIOUS ACTIVITY REPORT (draft) — address {alert.address}",
        f"Alert score: {alert.score:.2f} (model {alert.ml_score:.2f}).",
        "Typologies detected:",
    ]
    for hit in alert.typologies:
        lines.append(f"  - {hit.name}: {hit.detail} (severity {hit.severity:.1f})")
    f = alert.features
    lines.append(
        f"Flow: {f.get('total_in', 0):,.0f} in over {f.get('in_count', 0)} transfers from "
        f"{f.get('unique_in', 0)} sources; {f.get('total_out', 0):,.0f} out to "
        f"{f.get('unique_out', 0)} destinations."
    )
    lines.append("A human analyst must review this draft before filing a SAR.")
    return "\n".join(lines)


def llm_report(alert: Alert, llm: LLMClient | None = None, provider_spec: str | None = None) -> str:
    client = llm or (build_llm(provider_spec) if provider_spec else build_llm())
    typ = "; ".join(f"{h.name} ({h.detail})" for h in alert.typologies)
    prompt = (
        f"Address: {alert.address}. Alert score: {alert.score:.2f}. "
        f"Typologies: {typ}. Features: {alert.features}. Write the report."
    )
    return client.complete(_SYSTEM, prompt, max_tokens=300).text.strip()


def build_report(
    alert: Alert,
    mode: str = "template",
    llm: LLMClient | None = None,
    provider_spec: str | None = None,
) -> str:
    if mode == "llm" or llm is not None:
        try:
            return llm_report(alert, llm=llm, provider_spec=provider_spec)
        except Exception:  # a configured provider failed; fall back to the template
            pass
    return template_report(alert)
