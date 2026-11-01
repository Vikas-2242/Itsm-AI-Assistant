"""Agent orchestration: MCP read, RAG retrieval, explicit decision and grounded response."""
import asyncio
from mcp_client import call_tool
from rag import search
from llm_service import generate_recommendation
from audit import log_event


def _call(tool: str, args: dict | None = None):
    return asyncio.run(call_tool(tool, args or {}))


def analyze_incident(incident_id: str) -> dict:
    incident = _call("get_incident_tool", {"incident_id": incident_id})
    query = " ".join(str(incident.get(k, "")) for k in ("application", "category", "short_description", "description"))
    kedb = search(query, "kedb", 3)
    top_score = kedb[0]["similarity"] if kedb else 0.0
    # Thresholds are demo assumptions, not prescribed by the assignment.
    if kedb and top_score >= 0.52:
        path = "high_confidence"
        reason = f"Review {kedb[0]['known_error_id']} and verify its documented conditions before using the workaround."
    elif kedb and top_score >= 0.30:
        path = "ambiguous"
        reason = "Compare the candidate KEDB record with historical cases and collect diagnostics before selecting a fix."
    else:
        path = "no_match"
        reason = "No sufficiently similar KEDB record was found; gather diagnostics and escalate or investigate further."
    history = []
    if path != "high_confidence":
        history = search(query, "resolved", 3)
    decision = {"path": path, "reason": reason, "top_similarity": top_score, "thresholds": {"high_confidence": 0.52, "partial": 0.30}}
    recommendation, llm_mode = generate_recommendation(incident, kedb, history, decision)
    result = {"incident": incident, "kedb": kedb, "history": history, "decision": decision, "recommendation": recommendation, "llm_mode": llm_mode}
    log_event("incident_analysis", {"incident_id": incident_id, "decision_path": path, "kedb_ids": [x.get("known_error_id") for x in kedb], "history_ids": [x.get("incident_id") for x in history], "top_similarity": top_score, "llm_mode": llm_mode})
    return result


def execute_approved_write(incident_id: str, operation: str, value: str, approval_token: str) -> dict:
    # MCP server independently validates the signed, action-bound approval token.
    result = _call("update_incident_tool", {"incident_id": incident_id, "operation": operation, "value": value, "approval_token": approval_token})
    log_event("approved_action_returned", {"incident_id": incident_id, "operation": operation, "success": bool(result.get("success"))})
    return result
