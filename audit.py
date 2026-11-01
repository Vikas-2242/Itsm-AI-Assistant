"""Append-only JSON Lines audit trail for demo runs."""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from threading import Lock

_PATH = Path(__file__).resolve().parent / "audit.log"
_LOCK = Lock()
_IST = ZoneInfo("Asia/Kolkata")

def log_event(event_type: str, details: dict) -> None:
    row = {"timestamp": datetime.now(_IST).isoformat(), "event": event_type, "details": details}
    with _LOCK, _PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_events(limit: int = 100) -> list[dict]:
    if not _PATH.exists():
        return []
    rows = []
    with _PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:][::-1]

