# ITSM Incident Resolution & Known Error Assistant

A junior-level, local-first demonstration aligned with `Requirement.pdf`: incident retrieval, semantic KEDB retrieval, historical incident search, evidence-grounded recommendations, MCP tools, human approval, audit events, and an Azure deployment approach.

> **Safety / scope:** All data is synthetic. This is a demo, not a production ITSM integration. Do not use real customer/incident data. No write action should be described as successful unless the MCP tool confirms success.

## Stack
- Python 3.11 recommended
- Streamlit UI
- ChromaDB persistent vector store
- Sentence Transformers `all-MiniLM-L6-v2` embeddings
- MCP Python SDK over stdio
- Optional OpenAI-compatible chat-completions endpoint
- JSON files as the mock ITSM service

## 1. Setup (Windows PowerShell)

```powershell
cd itsm-ai-assistant
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` if you have an OpenAI-compatible endpoint:

```dotenv
LLM_BASE_URL=https://provider.example/v1
LLM_API_KEY=your_key_here
LLM_MODEL=your_model_name
LLM_ENABLED=true
APPROVAL_SIGNING_SECRET=replace-with-a-long-random-secret
```

If no API access is ready, set `LLM_ENABLED=false`. The app still performs MCP retrieval, semantic search, decisioning, audit logging, and uses a deterministic evidence-grounded fallback response.

## 2. Setup (macOS/Linux)

```bash
cd itsm-ai-assistant
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## 3. Run

From the project root, with the virtual environment activated:

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`). First startup may download the embedding model; allow time and internet access. The MCP server is launched by the client over stdio as needed.

## 4. Demo walkthrough

1. Analyze `INC001245`: expected strong candidate match to `KE0042`.
2. Analyze `INC001246` or `INC001247`: review retrieved evidence and historical cases. Since the sample dataset is small, check the displayed similarity and do not overstate certainty.
3. Approve an `add_work_note` action and verify the MCP success response and updated incident JSON.
4. Propose another action and reject it; the write tool must not be called.
5. Enter a nonexistent incident ID and confirm a useful error is displayed.
6. Expand the audit trail and show analysis, approval, tool result and failures.

## 5. Tests

```bash
python -m pytest
```

If pytest is not installed, add `pytest` to the development environment (`pip install pytest`).

## 6. Data and reset

Sample data is in `data/incidents.json`, `data/kedb.json`, and `data/resolved_incidents.json`. Approved demo writes modify `incidents.json`. To reset, restore the original sample file from version control or re-extract a clean copy. Chroma's local index is stored in `.chroma/` and can be removed to rebuild it.

## 7. Azure deployment approach (documented, not provisioned)

For a small demo, use Azure App Service or Azure Container Apps for the Python web app. Configure `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, and `APPROVAL_SIGNING_SECRET` as environment variables; store production secrets in Azure Key Vault. Package the app and its MCP server in the same container/process environment, and ensure the hosting setup permits subprocess/stdio MCP transport. Use persistent storage for ChromaDB and audit records or move them to managed storage. Replace local JSON files with a real service/database only after adding authentication, authorization, concurrency control, backups, and operational monitoring. Validate the selected hosting plan supports persistent disk and subprocess needs before deployment.

## Architecture

`Streamlit UI -> agent orchestration -> MCP client -> MCP stdio server -> mock ITSM JSON service`

The agent separately uses `Sentence Transformers -> ChromaDB` for KEDB and resolved-incident retrieval. The optional LLM receives the incident and retrieved evidence, not unrestricted access to the data store. The MCP write tool validates a short-lived HMAC approval token bound to the exact incident, operation, and value.

## Known limitations / honest assumptions

- KEDB similarity thresholds (0.52 strong candidate, 0.30 partial) are demo heuristics, not validated operational thresholds.
- Sample records are intentionally tiny; retrieval quality must be tested on a labelled dataset for real use.
- JSON storage is for a single-user demo and is not transaction-safe for concurrent users.
- The local approval secret is for development only; set a strong secret in the environment before sharing/deploying.
- The Azure approach is documented; no Azure resources are created by this repository.
- The application can run without an LLM key using its deterministic fallback. This fallback is not a substitute for a configured LLM in an assessment requiring live LLM inference.
