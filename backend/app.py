from __future__ import annotations

import copy
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

from .agent import SakugaCutAgent
from .config import settings
from .json_utils import read_json, to_plain, write_json
from .knowledge import build_profile_from_video, get_profile, list_profiles, new_profile_id, profile_work_dir
from .models import JobState
from .phase1 import Phase1Analyzer
from .storage import (
    add_progress,
    init_status,
    job_dir,
    load_status,
    mark_error,
    safe_artifact_path,
    save_status,
    set_state,
)


app = Flask(__name__)
CORS(app)

_threads: dict[str, threading.Thread] = {}


@app.get("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "ark_pro": bool(settings.ark_api_key and settings.ark_model),
            "ark_lite": bool(settings.ark_lite_api_key and settings.ark_lite_model),
        }
    )


@app.post("/api/jobs")
def create_job():
    asset_files = [file for file in request.files.getlist("assets") if file.filename]
    if not asset_files:
        return jsonify({"error": "at least one user asset is required"}), 400

    job_id = uuid.uuid4().hex[:12]
    root = job_dir(job_id)
    upload_dir = root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    sample_paths: list[str] = []
    sample_files = [file for file in request.files.getlist("samples") if file.filename]
    for idx, file in enumerate(sample_files):
        sample_paths.append(str(_save_upload(file, upload_dir, f"sample_{idx + 1}")))

    asset_paths: list[str] = []
    for idx, file in enumerate(asset_files):
        asset_paths.append(str(_save_upload(file, upload_dir, f"asset_{idx + 1}")))

    target_requirement = request.form.get("target_requirement", "").strip()
    knowledge_profile_ids = _form_list("knowledge_profile_ids")
    write_json(
        root / "manifest.json",
        {
            "sample_paths": sample_paths,
            "asset_paths": asset_paths,
            "target_requirement": target_requirement,
            "knowledge_profile_ids": knowledge_profile_ids,
        },
    )
    status = init_status(job_id)
    status.artifacts["manifest"] = "manifest.json"
    save_status(status)
    return jsonify(_status_payload(job_id))


@app.get("/api/runs")
def list_runs():
    runs: list[dict] = []
    for root in settings.runs_dir.iterdir():
        if not root.is_dir():
            continue
        job_id = root.name
        payload = _status_payload(job_id)
        manifest = read_json(root / "manifest.json", {}) or {}
        sample_paths = manifest.get("sample_paths")
        if not isinstance(sample_paths, list):
            sample_paths = []
        payload["sample_names"] = [Path(str(path)).name for path in sample_paths or []]
        payload["sample_name"] = " / ".join(payload["sample_names"])
        payload["target_requirement"] = str(manifest.get("target_requirement") or "")
        payload["asset_count"] = len(manifest.get("asset_paths") or [])
        payload["mtime"] = root.stat().st_mtime
        runs.append(payload)
    runs.sort(key=lambda item: float(item.get("mtime") or 0), reverse=True)
    return jsonify({"runs": runs})


@app.post("/api/jobs/<job_id>/run")
def run_job(job_id: str):
    _start_thread(job_id, _run_full)
    return jsonify(_status_payload(job_id))


@app.post("/api/jobs/<job_id>/phase1")
def run_phase1(job_id: str):
    _start_thread(job_id, _run_phase1)
    return jsonify(_status_payload(job_id))


@app.post("/api/jobs/<job_id>/phase2")
def run_phase2(job_id: str):
    _start_thread(job_id, _run_phase2)
    return jsonify(_status_payload(job_id))


@app.post("/api/jobs/<job_id>/revisions")
def create_revision(job_id: str):
    data = request.get_json(silent=True) or {}
    instruction = str(data.get("instruction") or "").strip()
    if not instruction:
        return jsonify({"error": "revision instruction is required"}), 400

    parent_root = job_dir(job_id)
    if not parent_root.exists():
        return jsonify({"error": "parent job not found"}), 404

    parent_status = load_status(job_id)
    if parent_status.state != JobState.done:
        return jsonify({"error": "parent job must be done before creating a revision"}), 400

    missing = [
        rel
        for rel in ("analysis.json", "plan.json", "output.mp4")
        if not (parent_root / rel).exists()
    ]
    if missing:
        return jsonify({"error": f"parent job is missing required artifacts: {', '.join(missing)}"}), 400

    parent_manifest = read_json(parent_root / "manifest.json", {}) or {}
    parent_context = read_json(parent_root / "revision_context.json", {}) or {}
    base_job_id = str(parent_manifest.get("base_job_id") or parent_context.get("base_job_id") or job_id)
    revision_index = _next_revision_index(base_job_id)

    child_id = uuid.uuid4().hex[:12]
    child_root = job_dir(child_id)
    child_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "sample_paths": list(parent_manifest.get("sample_paths") or []),
        "asset_paths": list(parent_manifest.get("asset_paths") or []),
        "target_requirement": str(parent_manifest.get("target_requirement") or ""),
        "knowledge_profile_ids": list(parent_manifest.get("knowledge_profile_ids") or []),
        "parent_job_id": job_id,
        "base_job_id": base_job_id,
        "revision_instruction": instruction,
        "revision_index": revision_index,
    }
    write_json(child_root / "manifest.json", manifest)

    analysis = _analysis_for_revision(read_json(parent_root / "analysis.json", {}) or {}, child_id)
    write_json(child_root / "analysis.json", analysis)

    previous_script_path = parent_root / "video_script.md"
    previous_script = previous_script_path.read_text(encoding="utf-8") if previous_script_path.exists() else ""
    history = _revision_history(parent_context, parent_manifest, job_id)
    revision_context = {
        "job_id": child_id,
        "parent_job_id": job_id,
        "base_job_id": base_job_id,
        "revision_index": revision_index,
        "instruction": instruction,
        "previous": {
            "job_id": job_id,
            "plan": read_json(parent_root / "plan.json", {}) or {},
            "video_script": previous_script,
            "output": "output.mp4",
        },
        "history": history,
    }
    write_json(child_root / "revision_context.json", revision_context)

    status = init_status(child_id)
    status.artifacts["manifest"] = "manifest.json"
    status.artifacts["analysis"] = "analysis.json"
    status.artifacts["revision_context"] = "revision_context.json"
    save_status(status)

    _start_thread(child_id, _run_phase2)
    return jsonify(_status_payload(child_id))


@app.get("/api/jobs/<job_id>")
def get_job(job_id: str):
    return jsonify(_status_payload(job_id))


@app.get("/api/jobs/<job_id>/json/<name>")
def get_job_json(job_id: str, name: str):
    allowed = {
        "manifest": "manifest.json",
        "analysis": "analysis.json",
        "plan": "plan.json",
        "status": "status.json",
        "knowledge_selection": "knowledge_selection.json",
        "revision_context": "revision_context.json",
    }
    rel = allowed.get(name)
    if not rel:
        return jsonify({"error": "unknown json artifact"}), 404
    data = read_json(job_dir(job_id) / rel)
    if data is None:
        return jsonify({"error": "artifact not found"}), 404
    return jsonify(data)


@app.get("/api/knowledge-profiles")
def api_list_knowledge_profiles():
    return jsonify({"profiles": list_profiles(include_content=False)})


@app.get("/api/knowledge-profiles/<profile_id>")
def api_get_knowledge_profile(profile_id: str):
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "knowledge profile not found"}), 404
    return jsonify(profile)


@app.post("/api/knowledge-profiles")
def api_create_knowledge_profile():
    video = request.files.get("video")
    if not video or not video.filename:
        return jsonify({"error": "video file is required"}), 400
    profile_id = new_profile_id()
    upload_dir = profile_work_dir(profile_id) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    video_path = _save_upload(video, upload_dir, "knowledge")
    summary = request.form.get("summary", "").strip()
    try:
        profile = build_profile_from_video(profile_id, video_path, summary)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(profile)


@app.get("/api/jobs/<job_id>/artifacts/<path:rel_path>")
def artifact(job_id: str, rel_path: str):
    try:
        target = safe_artifact_path(job_id, rel_path)
    except ValueError:
        return jsonify({"error": "invalid artifact path"}), 400
    if not target.exists():
        return jsonify({"error": "artifact not found"}), 404
    return send_file(target)


def _start_thread(job_id: str, fn) -> None:
    old = _threads.get(job_id)
    if old and old.is_alive():
        add_progress(job_id, "job already running")
        return
    thread = threading.Thread(target=fn, args=(job_id,), daemon=True)
    _threads[job_id] = thread
    thread.start()


def _run_full(job_id: str) -> None:
    try:
        _run_phase1(job_id)
        if load_status(job_id).state != JobState.error:
            _run_phase2(job_id)
    except Exception as exc:
        mark_error(job_id, str(exc))


def _run_phase1(job_id: str) -> None:
    root = job_dir(job_id)
    try:
        set_state(job_id, JobState.phase1_running, "phase1 started")
        Phase1Analyzer().run(job_id, root)
        set_state(job_id, JobState.phase1_done, "phase1 done")
    except Exception as exc:
        mark_error(job_id, str(exc))


def _run_phase2(job_id: str) -> None:
    root = job_dir(job_id)
    try:
        set_state(job_id, JobState.phase2_running, "phase2 started")
        SakugaCutAgent(job_id, root).run()
        set_state(job_id, JobState.done, "phase2 done")
    except Exception as exc:
        mark_error(job_id, str(exc))


def _save_upload(file, upload_dir: Path, prefix: str) -> Path:
    name = Path(file.filename or "upload").name.replace("/", "_").replace("\\", "_")
    target = upload_dir / f"{prefix}_{name}"
    file.save(target)
    return target


def _form_list(name: str) -> list[str]:
    values = request.form.getlist(name)
    if not values and request.form.get(name):
        values = [request.form.get(name, "")]
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _status_payload(job_id: str) -> dict:
    status = load_status(job_id)
    data = to_plain(status)
    manifest = read_json(job_dir(job_id) / "manifest.json", {}) or {}
    artifacts = _existing_artifacts(job_id, status.artifacts)
    data["artifacts"] = artifacts
    data["artifact_urls"] = {
        name: f"/api/jobs/{job_id}/artifacts/{rel}" for name, rel in artifacts.items()
    }
    data.update(_revision_fields(job_id, manifest))
    return data


def _existing_artifacts(job_id: str, recorded: dict[str, str]) -> dict[str, str]:
    root = job_dir(job_id)
    discovered = {
        "manifest": "manifest.json",
        "analysis": "analysis.json",
        "plan": "plan.json",
        "status": "status.json",
        "events": "events.jsonl",
        "knowledge_selection": "knowledge_selection.json",
        "hyperframes": "hyperframes/index.html",
        "output": "output.mp4",
        "video_script": "video_script.md",
        "revision_context": "revision_context.json",
    }
    artifacts: dict[str, str] = {}
    for name, rel in recorded.items():
        try:
            if safe_artifact_path(job_id, rel).exists():
                artifacts[name] = rel
        except ValueError:
            continue
    for name, rel in discovered.items():
        if (root / rel).exists():
            artifacts[name] = rel
    return artifacts


def _float_or_none(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _revision_fields(job_id: str, manifest: dict) -> dict:
    parent_job_id = str(manifest.get("parent_job_id") or "")
    base_job_id = str(manifest.get("base_job_id") or (job_id if not parent_job_id else parent_job_id))
    revision_instruction = str(manifest.get("revision_instruction") or "")
    revision_index = manifest.get("revision_index")
    if revision_index is None:
        revision_index = 0 if not parent_job_id else None
    return {
        "parent_job_id": parent_job_id or None,
        "base_job_id": base_job_id or job_id,
        "revision_instruction": revision_instruction,
        "revision_index": revision_index,
    }


def _next_revision_index(base_job_id: str) -> int:
    max_index = 0
    for root in settings.runs_dir.iterdir():
        if not root.is_dir():
            continue
        manifest = read_json(root / "manifest.json", {}) or {}
        fields = _revision_fields(root.name, manifest)
        if fields["base_job_id"] != base_job_id:
            continue
        value = fields.get("revision_index")
        if isinstance(value, (int, float)):
            max_index = max(max_index, int(value))
    return max_index + 1


def _analysis_for_revision(parent_analysis: dict, child_id: str) -> dict:
    analysis = copy.deepcopy(parent_analysis)
    analysis["job_id"] = child_id
    assets = analysis.get("assets")
    if isinstance(assets, list):
        analysis["assets"] = [
            asset
            for asset in assets
            if not _is_generated_tts_asset(asset)
        ]
    return analysis


def _is_generated_tts_asset(asset: object) -> bool:
    if not isinstance(asset, dict):
        return False
    notes = asset.get("notes")
    if not isinstance(notes, list):
        return False
    return "generated_tts=true" in {str(item) for item in notes}


def _revision_history(parent_context: dict, parent_manifest: dict, parent_job_id: str) -> list[dict]:
    history = parent_context.get("history") if isinstance(parent_context, dict) else None
    rows = copy.deepcopy(history) if isinstance(history, list) else []
    parent_instruction = str(parent_manifest.get("revision_instruction") or "")
    if parent_instruction:
        rows.append(
            {
                "job_id": parent_job_id,
                "parent_job_id": parent_manifest.get("parent_job_id"),
                "revision_index": parent_manifest.get("revision_index"),
                "instruction": parent_instruction,
            }
        )
    return rows


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
