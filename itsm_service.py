"""Synthetic ITSM data service. All writes are local demo writes."""
from __future__ import annotations
import json
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
_LOCK = Lock()


def _load(name: str):
    with (DATA / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(name: str, value):
    with (DATA / name).open("w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)


def get_incident(incident_id: str) -> dict:
    with _LOCK:
        records = _load("incidents.json")
        for item in records:
            if item["incident_id"].lower() == incident_id.strip().lower():
                return item
    raise ValueError(f"Incident '{incident_id}' was not found.")

def update_incident(incident_id: str, operation: str, value: str) -> dict:
    """Write operation. Caller must enforce approval before invoking this function."""
    if operation not in {"add_work_note", "set_status"}:
        raise ValueError("Unsupported operation. Use add_work_note or set_status.")
    if not value.strip():
        raise ValueError("Update value cannot be empty.")

    with _LOCK:
        records = _load("incidents.json")
        for item in records:
            if item["incident_id"].lower() == incident_id.strip().lower():
                if operation == "add_work_note":
                    note = value.strip()
                    work_notes = item.setdefault("work_notes", [])

                    if note in work_notes:
                        return {
                            "success": True,
                            "incident": item,
                            "message": "Work note already exists; duplicate was not added."
                        }

                    work_notes.append(note)
                else:
                    if value not in {"Open", "In Progress", "Resolved", "Closed"}:
                        raise ValueError("Invalid status value.")
                    item["status"] = value

                _save("incidents.json", records)
                return {
                    "success": True,
                    "incident": item,
                    "message": f"{operation} completed."
                }

    raise ValueError(f"Incident '{incident_id}' was not found.")


def list_kedb() -> list[dict]:
    return _load("kedb.json")


def list_resolved_incidents() -> list[dict]:
    return _load("resolved_incidents.json")
