from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


HEARTBEAT_PATH = Path(".runtime") / "worker_heartbeat.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_worker_heartbeat(status: str = "RUNNING") -> None:
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(json.dumps({"status": status, "updated_at": utc_now_iso()}), encoding="utf-8")


def read_worker_status(max_age_seconds: int = 20) -> dict:
    if not HEARTBEAT_PATH.exists():
        return {"status": "OFFLINE", "updated_at": None, "age_seconds": None}
    try:
        payload = json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8"))
        updated_at = datetime.fromisoformat(payload["updated_at"])
        age = (datetime.now(timezone.utc) - updated_at).total_seconds()
        status = payload.get("status", "UNKNOWN") if age <= max_age_seconds else "STALE"
        return {"status": status, "updated_at": payload.get("updated_at"), "age_seconds": int(age)}
    except Exception:
        return {"status": "UNKNOWN", "updated_at": None, "age_seconds": None}
