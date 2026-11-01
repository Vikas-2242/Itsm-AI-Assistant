from __future__ import annotations

import streamlit as st

from agent import analyze_incident, execute_approved_write
from approval import issue_token
from audit import read_events, log_event
from itsm_service import get_incident


st.set_page_config(
    page_title="ITSM Incident Assistant",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ ITSM Incident Resolution & Known Error Assistant")
st.caption(
    "Synthetic demo environment · RAG-grounded recommendations · "
    "MCP tools · human approval required for writes"
)


# -----------------------------
# Session state
# -----------------------------
if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

if "last_action_result" not in st.session_state:
    st.session_state.last_action_result = None


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("Demo controls")
    st.write("Try the supplied incident IDs:")
    st.code("INC001245\nINC001246\nINC001247")
    st.info(
        "Data is synthetic and stored locally in data/incidents.json. "
        "Do not use real production data."
    )
    st.caption(
        "Similarity thresholds are demo assumptions and should be calibrated "
        "with labelled examples."
    )


# -----------------------------
# Incident investigation
# -----------------------------
st.subheader("1. Investigate an incident")

with st.form("incident_form"):
    incident_id_input = st.text_input(
        "Incident ID",
        value="INC001245",
        help="Example: INC001245",
    )
    submitted = st.form_submit_button(
        "Retrieve and analyze",
        type="primary",
    )

if submitted:
    st.session_state.last_action_result = None
    st.session_state.pending_action = None
    st.session_state.analysis = None

    incident_id_input = incident_id_input.strip()

    try:
        # Check first so a missing ID gets a clear message.
        get_incident(incident_id_input)
    except ValueError:
        log_event(
            "analysis_error",
            {
                "incident_id": incident_id_input,
                "error_type": "IncidentNotFound",
                "message": f"Incident '{incident_id_input}' was not found.",
            },
        )
        st.error(
            f"Incident {incident_id_input} was not found. "
            "Please check the ID and try again."
        )
    else:
        try:
            with st.spinner(
                "Retrieving incident through MCP, searching the vector database, "
                "and preparing evidence..."
            ):
                st.session_state.analysis = analyze_incident(incident_id_input)

        except Exception as exc:
            log_event(
                "analysis_error",
                {
                    "incident_id": incident_id_input,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
            )
            st.error(
                "Could not analyze this incident due to an unexpected error. "
                "Please try again or check the application logs."
            )


# -----------------------------
# Display analysis and proposed action
# -----------------------------
analysis = st.session_state.analysis

if analysis:
    incident = analysis["incident"]
    decision = analysis["decision"]

    st.divider()
    st.subheader("2. Incident details")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Incident", incident["incident_id"])
    c2.metric("Priority", incident.get("priority", "Unknown"))
    c3.metric("Status", incident.get("status", "Unknown"))
    c4.metric(
        "Decision path",
        decision["path"].replace("_", " ").title(),
    )

    st.write(f"**Application:** {incident.get('application', 'Unknown')}")
    st.write(f"**Description:** {incident.get('description', '')}")

    st.subheader("3. Retrieved KEDB evidence (RAG)")

    if analysis["kedb"]:
        st.dataframe(
            [
                {
                    "Record ID": item.get("known_error_id"),
                    "Title": item.get("title"),
                    "Similarity": item.get("similarity"),
                    "Symptoms": item.get("symptoms"),
                    "Root cause (recorded)": item.get("root_cause"),
                    "Status": item.get("status"),
                }
                for item in analysis["kedb"]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("No KEDB records were returned.")

    if analysis["history"]:
        st.subheader("Historical resolved incidents")
        st.dataframe(
            [
                {
                    "Incident ID": item.get("incident_id"),
                    "Title": item.get("title"),
                    "Similarity": item.get("similarity"),
                    "Resolution": item.get("resolution"),
                }
                for item in analysis["history"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("4. Grounded recommendation")
    st.caption(f"Response mode: {analysis['llm_mode']}")
    st.markdown(analysis["recommendation"])
    # Always display the current notes from the incident record,
# not from the generated recommendation text.
    st.subheader("Current work notes")

    current_notes = incident.get("work_notes", [])

    if isinstance(current_notes, list) and current_notes:
        for note in current_notes:
            st.markdown(f"- {note}")
    elif isinstance(current_notes, str) and current_notes.strip():
        st.markdown(f"- {current_notes}")
    else:
        st.caption("No work notes recorded.")

        st.subheader("5. Proposed action — approval required")

    # Keep this outside the form so changing the operation updates the fields.
    operation = st.selectbox(
        "Operation",
        ["add_work_note", "set_status"],
        format_func=lambda option: (
            "Add work note"
            if option == "add_work_note"
            else "Change status"
        ),
        key="action_operation",
    )

    default_note = (
        f"Investigating based on retrieved evidence "
        f"{analysis['kedb'][0]['known_error_id']}. "
        "Verify the documented conditions before applying any workaround."
        if analysis["kedb"]
        else "Further diagnostics required; no adequate KEDB match found."
    )

    with st.form("action_form"):
        if operation == "set_status":
            value = st.selectbox(
                "Proposed status",
                ["Open", "In Progress", "Resolved", "Closed"],
                index=1,
                key="proposed_status",
            )
        else:
            value = st.text_area(
                "Proposed work note",
                value=default_note,
                key="proposed_work_note",
            )

        st.warning(
            "Nothing is written until you click Approve and execute. "
            "The MCP server validates a signed, action-bound, short-lived "
            "approval token."
        )

        approve = st.form_submit_button(
            "Approve and execute via MCP",
            type="primary",
        )
        reject = st.form_submit_button("Reject proposal")

    if reject:
        log_event(
            "human_rejected_action",
            {
                "incident_id": incident["incident_id"],
                "operation": operation,
            },
        )
        st.session_state.pending_action = None
        st.info("Action rejected. No write tool was called.")

    elif approve:
        if not value.strip():
            st.error("Please enter a non-empty proposed value.")
        else:
            token = issue_token(
                incident["incident_id"],
                operation,
                value.strip(),
            )

            log_event(
                "human_approved_action",
                {
                    "incident_id": incident["incident_id"],
                    "operation": operation,
                    "value": value.strip(),
                },
            )

            try:
                with st.spinner("Executing approved MCP tool..."):
                    outcome = execute_approved_write(
                        incident["incident_id"],
                        operation,
                        value.strip(),
                        token,
                    )

                if outcome.get("success"):
                    incident_id = incident["incident_id"]

                    # Reload the incident after the MCP write.
                    updated_incident = get_incident(incident_id)

                    # Rerun analysis so Observed Facts and the recommendation
                    # are generated from the latest incident and work notes.
                    with st.spinner(
                        "Refreshing incident facts and recommendation..."
                    ):
                        refreshed_analysis = analyze_incident(incident_id)

                    # Keep the refreshed incident and analysis in session state.
                    refreshed_analysis["incident"] = updated_incident
                    st.session_state.analysis = refreshed_analysis

                    # Preserve the successful MCP result after the rerun.
                    st.session_state.last_action_result = outcome
                    st.session_state.pending_action = None

                    st.rerun()

                else:
                    st.error(
                        "MCP did not confirm success. "
                        "Check the tool response and audit log."
                    )
                    st.json(outcome)

            except Exception as exc:
                log_event(
                    "write_error",
                    {
                        "incident_id": incident["incident_id"],
                        "operation": operation,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    },
                )
                st.error(
                    "Write operation failed; do not assume the ticket changed. "
                    f"Details: {exc}"
                )


# Show the saved MCP result after the successful-write rerun.
if st.session_state.last_action_result:
    st.success("MCP confirmed the write operation succeeded.")
    st.json(st.session_state.last_action_result)


# -----------------------------
# Audit trail
# -----------------------------
st.divider()

with st.expander("Audit trail (latest 100 events)", expanded=False):
    events = read_events(100)

    if events:
        st.dataframe(
            events,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No audit events yet. Run an analysis to populate the audit trail.")


# -----------------------------
# Architecture and limitations
# -----------------------------
with st.expander("Architecture and limitations"):
    st.markdown(
        """
        - **UI:** Streamlit
        - **Agent/API logic:** Python orchestration
        - **RAG:** Sentence Transformers embeddings + persistent ChromaDB semantic search
        - **Tool execution:** MCP Python SDK over stdio; incident reads and writes are MCP tools
        - **Safety:** Explicit UI approval plus an action-bound, expiring HMAC token validated by the MCP server
        - **Data:** Synthetic JSON only; no live ServiceNow/Jira connection
        - **LLM:** Optional OpenAI-compatible chat-completions endpoint configured via environment variables; grounded deterministic fallback works without credentials
        - **Known limitations:** Similarity thresholds are heuristic; sample dataset is tiny; the local JSON store is not multi-user/production-safe; Azure deployment is documented, not provisioned automatically
        """
    )