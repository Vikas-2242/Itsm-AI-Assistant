"""Optional OpenAI-compatible chat completion integration with safe fallback."""
import os
import httpx
from dotenv import load_dotenv
load_dotenv()


def generate_recommendation(incident: dict, kedb: list[dict], history: list[dict], decision: dict) -> tuple[str, str]:
    evidence = {"incident": incident, "kedb_evidence": kedb, "historical_evidence": history, "decision": decision}
    enabled = os.getenv("LLM_ENABLED", "true").lower() in {"1", "true", "yes"}
    base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "")
    if enabled and base_url and api_key and model and api_key != "replace_me":
        prompt = (
            "You are an ITSM incident assistant. Use ONLY supplied evidence for factual claims. "
            "Separate observed facts from hypotheses, state uncertainty, cite record IDs, and never claim a fix was executed. "
            "Recommend diagnostics/escalation if evidence is insufficient. Return concise Markdown.\n\n"
            + __import__("json").dumps(evidence, ensure_ascii=False)
        )
        try:
            response = httpx.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "system", "content": "Be evidence-grounded, cautious, and concise."}, {"role": "user", "content": prompt}], "temperature": 0.1},
                timeout=25.0,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return content, "configured LLM"
        except Exception as exc:
            fallback = _fallback(incident, kedb, history, decision)
            return fallback + f"\n\n*LLM unavailable; used deterministic fallback ({type(exc).__name__}).*", "fallback after LLM error"
    return _fallback(incident, kedb, history, decision), "deterministic fallback (LLM not configured)"

def _fallback(
    incident: dict,
    kedb: list[dict],
    history: list[dict],
    decision: dict,
) -> str:
    work_notes = incident.get("work_notes", [])

    if isinstance(work_notes, list):
        notes_text = "\n".join(
            f"- {note}" for note in work_notes if str(note).strip()
        )
    elif work_notes:
        notes_text = str(work_notes).strip()
    else:
        notes_text = ""

    lines = [
        f"### Incident {incident['incident_id']}: "
        f"{incident.get('short_description', '')}",
        "",
        "**Observed facts**",
        f"- Application: {incident.get('application', 'Unknown')}",
        f"- Priority/status: {incident.get('priority', 'Unknown')} / "
        f"{incident.get('status', 'Unknown')}",
        f"- Description: {incident.get('description', '')}",
    ]

    if notes_text:
        lines += ["- Work notes:", notes_text]
    else:
        lines += ["- Work notes: None recorded"]

    lines.append("")

    if kedb:
        top = kedb[0]
        lines += [
            "**Retrieved KEDB evidence**",
            f"- {top.get('known_error_id')} — {top.get('title')} "
            f"(similarity: {top.get('similarity', 0):.3f})",
            f"- Recorded root cause: {top.get('root_cause', 'Not specified')}",
            f"- Documented workaround: {top.get('workaround', 'Not specified')}",
            f"- Documented resolution: {top.get('resolution', 'Not specified')}",
            "",
            "**Assessment**",
            "The retrieved record is a candidate match, not proof that the current "
            "incident has the same root cause. Verify current service and database "
            "metrics before applying the workaround.",
        ]
    else:
        lines += [
            "**Assessment**",
            "No KEDB evidence was retrieved. Do not assume a root cause; "
            "collect diagnostics and consider escalation.",
        ]

    if history:
        lines += ["", "**Historical evidence**"]
        for item in history[:2]:
            lines.append(
                f"- {item.get('incident_id')}: {item.get('title')} "
                f"(similarity: {item.get('similarity', 0):.3f}) — "
                f"{item.get('resolution', '')}"
            )

    lines += [
        "",
        f"**Next step:** {decision['reason']}",
        "No ticket change has been made. Review the proposed action and "
        "explicitly approve it before execution.",
    ]

    return "\n".join(lines)
