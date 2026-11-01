"""MCP server exposing synthetic ITSM tools over stdio."""
from mcp.server.fastmcp import FastMCP
from itsm_service import get_incident, update_incident, list_kedb, list_resolved_incidents
from approval import verify_token
from audit import log_event

mcp = FastMCP("synthetic-itsm")

@mcp.tool()
def get_incident_tool(incident_id: str) -> dict:
    """Read an incident by ID from the synthetic ITSM service."""
    result = get_incident(incident_id)
    log_event("mcp_read_incident", {"incident_id": incident_id, "success": True})
    return result

@mcp.tool()
def search_kedb_records() -> list[dict]:
    """Return synthetic known-error records for the RAG index."""
    return list_kedb()

@mcp.tool()
def search_resolved_incidents() -> list[dict]:
    """Return synthetic resolved incidents for historical retrieval."""
    return list_resolved_incidents()

@mcp.tool()
def update_incident_tool(incident_id: str, operation: str, value: str, approval_token: str) -> dict:
    """Write to a ticket only with a valid, unexpired, action-bound approval token."""
    if not verify_token(approval_token, incident_id, operation, value):
        log_event("mcp_write_blocked", {"incident_id": incident_id, "operation": operation, "reason": "invalid_or_missing_approval"})
        raise ValueError("Write blocked: valid explicit human approval is required.")
    result = update_incident(incident_id, operation, value)
    log_event("mcp_write_result", {"incident_id": incident_id, "operation": operation, "success": bool(result.get("success"))})
    return result

if __name__ == "__main__":
    mcp.run(transport="stdio")
