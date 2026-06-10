from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from .config import settings
from .json_utils import read_json, to_plain, write_json
from .models import JobState, JobStatus


_lock = RLock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_name(name: str) -> str:
    safe = Path(name or "file").name.replace("/", "_").replace("\\", "_").strip()
    return safe or "file"


def job_dir(job_id: str) -> Path:
    return settings.runs_dir / clean_name(job_id)


def status_path(job_id: str) -> Path:
    return job_dir(job_id) / "status.json"


def events_path(job_id: str) -> Path:
    return job_dir(job_id) / "events.jsonl"


def load_status(job_id: str) -> JobStatus:
    data = read_json(status_path(job_id))
    if data:
        return JobStatus(**data)
    return JobStatus(job_id=job_id)


def save_status(status: JobStatus) -> JobStatus:
    with _lock:
        status.updated_at = now_iso()
        write_json(status_path(status.job_id), status)
    return status


def init_status(job_id: str) -> JobStatus:
    status = JobStatus(job_id=job_id)
    status.progress.append("job created")
    return save_status(status)


def set_state(job_id: str, state: JobState, msg: str | None = None) -> JobStatus:
    with _lock:
        status = load_status(job_id)
        status.state = state
        status.error = None if state != JobState.error else status.error
        if msg:
            status.progress.append(msg)
        return save_status(status)


def add_progress(job_id: str, msg: str) -> JobStatus:
    with _lock:
        status = load_status(job_id)
        status.progress.append(msg)
        return save_status(status)


def add_artifact(job_id: str, name: str, rel_path: str) -> JobStatus:
    with _lock:
        status = load_status(job_id)
        status.artifacts[name] = rel_path
        return save_status(status)


def log_event(
    job_id: str,
    event: str,
    message: str = "",
    data: dict[str, Any] | None = None,
    *,
    progress: bool = False,
) -> None:
    record = {
        "ts": now_iso(),
        "job_id": job_id,
        "event": event,
        "message": message,
        "data": _clip_value(to_plain(data or {})),
    }
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with _lock:
        path = events_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

        status = load_status(job_id)
        status.artifacts.setdefault("events", "events.jsonl")
        if progress and message:
            status.progress.append(message)
        save_status(status)

    suffix = f": {message}" if message else ""
    print(f"[sakugacut][{job_id}] {event}{suffix}", flush=True)


def mark_error(job_id: str, err: str) -> JobStatus:
    with _lock:
        path = events_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": now_iso(),
            "job_id": job_id,
            "event": "job.error",
            "message": err,
            "data": {},
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

        status = load_status(job_id)
        status.state = JobState.error
        status.error = err
        status.artifacts.setdefault("events", "events.jsonl")
        status.progress.append(f"error: {err}")
        print(f"[sakugacut][{job_id}] job.error: {err}", flush=True)
        return save_status(status)


def safe_artifact_path(job_id: str, rel_path: str) -> Path:
    root = job_dir(job_id).resolve()
    target = (root / rel_path).resolve()
    if root not in target.parents and target != root:
        raise ValueError("artifact path escapes job directory")
    return target


def _clip_value(value: Any, *, depth: int = 0, max_text: int = 4000, max_items: int = 40) -> Any:
    if depth > 6:
        return "<max-depth>"
    if isinstance(value, str):
        if len(value) <= max_text:
            return value
        return value[:max_text] + f"...<truncated {len(value) - max_text} chars>"
    if isinstance(value, list):
        clipped = [_clip_value(item, depth=depth + 1, max_text=max_text, max_items=max_items) for item in value[:max_items]]
        if len(value) > max_items:
            clipped.append(f"<truncated {len(value) - max_items} items>")
        return clipped
    if isinstance(value, dict):
        items = list(value.items())
        clipped = {
            str(key): _clip_value(item, depth=depth + 1, max_text=max_text, max_items=max_items)
            for key, item in items[:max_items]
        }
        if len(items) > max_items:
            clipped["<truncated>"] = f"{len(items) - max_items} items"
        return clipped
    return value
