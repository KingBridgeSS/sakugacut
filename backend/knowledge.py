from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ark import ArkError, json_schema_format, pro_client
from .config import settings
from .json_utils import extract_json, read_json, to_plain, write_json
from .models import AssetIR, MediaKind
from .phase1 import Phase1Analyzer


PROFILE_SUMMARY_INSTRUCTIONS = """你是短视频知识库编目助手。
根据 struct_info 为这个 knowledge profile 写一句简短简介，类似一个可选风格/结构标签。
要求：中文，20 字以内，具体说明结构或风格，不要泛泛写“短视频模板”。"""


PROFILE_SUMMARY_RESPONSE_FORMAT = json_schema_format(
    "knowledge_profile_summary",
    {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "一句简短中文简介，20 字以内。"},
        },
        "required": ["summary"],
        "additionalProperties": False,
    },
)


PROFILE_SELECT_INSTRUCTIONS = """你是 sakugacut 的知识库选择器。
你会看到用户素材 assets、目标要求 target_requirement，以及所有 knowledge profile 的一句简介。
只根据这些简介判断哪些 profile 可能对 Phase 2 创作有帮助。
可以不选，也可以选择多个；不要为了凑数而选择无关 profile。
返回 selected_ids 数组和简短 reason。"""


PROFILE_SELECT_RESPONSE_FORMAT = json_schema_format(
    "knowledge_profile_selection",
    {
        "type": "object",
        "properties": {
            "selected_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "选择的 knowledge profile id；可以为空数组。",
            },
            "reason": {"type": "string", "description": "简短说明选择依据。"},
        },
        "required": ["selected_ids", "reason"],
        "additionalProperties": False,
    },
)


def profile_store_dir() -> Path:
    path = settings.knowledge_dir / "profiles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def profile_work_dir(profile_id: str) -> Path:
    path = settings.knowledge_dir / "work" / clean_profile_id(profile_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_profile_id(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", value or "").strip("_")
    return text or uuid.uuid4().hex[:12]


def new_profile_id() -> str:
    return uuid.uuid4().hex[:12]


def profile_path(profile_id: str) -> Path:
    return profile_store_dir() / f"{clean_profile_id(profile_id)}.json"


def list_profiles(*, include_content: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in profile_store_dir().glob("*.json"):
        data = read_json(path, {}) or {}
        if not isinstance(data, dict):
            continue
        row = _public_profile(data, include_content=include_content)
        if row:
            rows.append(row)
    rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return rows


def get_profile(profile_id: str) -> dict[str, Any] | None:
    data = read_json(profile_path(profile_id), None)
    return data if isinstance(data, dict) else None


def get_profiles(profile_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for profile_id in profile_ids:
        clean_id = clean_profile_id(profile_id)
        if clean_id in seen:
            continue
        seen.add(clean_id)
        profile = get_profile(clean_id)
        if profile:
            rows.append(profile)
    return rows


def build_profile_from_video(profile_id: str, video_path: Path, summary: str = "") -> dict[str, Any]:
    profile_id = clean_profile_id(profile_id)
    work_dir = profile_work_dir(profile_id)
    analyzer = Phase1Analyzer()
    analyzer.set_raw_log_dir(work_dir / "llm_raw")
    asset = analyzer._analyze_asset("sample", "sample", video_path, work_dir)
    struct_info = analyzer.sample_struct_info([asset])
    final_summary = summary.strip() or generate_profile_summary(struct_info, video_path.name, raw_log_dir=work_dir / "llm_raw")
    profile = {
        "id": profile_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": final_summary,
        "struct_info": struct_info,
        "source_video_name": video_path.name,
        "source_video_path": str(video_path),
    }
    write_json(profile_path(profile_id), profile)
    return profile


def generate_profile_summary(struct_info: str, source_name: str = "", *, raw_log_dir: str | Path | None = None) -> str:
    fallback = _summary_fallback(struct_info, source_name)
    client = pro_client(raw_log_dir=raw_log_dir)
    if not client.enabled:
        return fallback
    payload = {
        "source_video_name": source_name,
        "struct_info": struct_info,
        "task": "为这个 knowledge profile 写一句简介。",
    }
    try:
        raw, _ = client.text(
            json.dumps(payload, ensure_ascii=False),
            instructions=PROFILE_SUMMARY_INSTRUCTIONS,
            response_format=PROFILE_SUMMARY_RESPONSE_FORMAT,
        )
        parsed = extract_json(raw)
        if isinstance(parsed, dict):
            summary = str(parsed.get("summary") or "").strip()
            if summary:
                return summary[:80]
    except Exception:
        return fallback
    return fallback


def select_profiles_for_analysis(
    assets: list[AssetIR],
    target_requirement: str,
    profiles: list[dict[str, Any]] | None = None,
    *,
    raw_log_dir: str | Path | None = None,
) -> dict[str, Any]:
    available = profiles if profiles is not None else list_profiles(include_content=False)
    summaries = [
        {"id": str(profile.get("id") or ""), "summary": str(profile.get("summary") or "")}
        for profile in available
        if str(profile.get("id") or "").strip()
    ]
    if not summaries:
        return {"selected_ids": [], "reason": "no knowledge profiles available"}

    client = pro_client(raw_log_dir=raw_log_dir)
    if not client.enabled:
        return {"selected_ids": [], "reason": "knowledge profile selector llm is unavailable"}

    payload = {
        "assets": [_asset_summary(asset) for asset in assets],
        "target_requirement": target_requirement,
        "knowledge_profile_summaries": summaries,
        "task": "选择适合注入 Phase 2 的 knowledge profile；可以不选或多选。",
    }
    try:
        raw, _ = client.text(
            json.dumps(payload, ensure_ascii=False),
            instructions=PROFILE_SELECT_INSTRUCTIONS,
            response_format=PROFILE_SELECT_RESPONSE_FORMAT,
        )
        parsed = extract_json(raw)
    except ArkError as exc:
        return {"selected_ids": [], "reason": f"knowledge profile selector llm error: {exc}"}
    except Exception as exc:
        return {"selected_ids": [], "reason": f"knowledge profile selector failed: {exc}"}

    allowed = {str(item["id"]) for item in summaries}
    selected: list[str] = []
    if isinstance(parsed, dict):
        for value in parsed.get("selected_ids") or []:
            profile_id = clean_profile_id(str(value))
            if profile_id in allowed and profile_id not in selected:
                selected.append(profile_id)
        reason = str(parsed.get("reason") or "").strip()
    else:
        reason = ""
    return {"selected_ids": selected, "reason": reason or "selector returned no reason"}


def _public_profile(profile: dict[str, Any], *, include_content: bool) -> dict[str, Any]:
    profile_id = str(profile.get("id") or "").strip()
    if not profile_id:
        return {}
    row = {
        "id": profile_id,
        "created_at": str(profile.get("created_at") or ""),
        "summary": str(profile.get("summary") or ""),
        "source_video_name": str(profile.get("source_video_name") or ""),
    }
    if include_content:
        row["struct_info"] = str(profile.get("struct_info") or "")
    return row


def _asset_summary(asset: AssetIR) -> dict[str, Any]:
    meta = None
    video_parts: list[dict[str, Any]] = []
    music_parts: list[dict[str, Any]] = []
    asr_parts: list[dict[str, Any]] = []
    if asset.video:
        meta = asset.video.meta
        video_parts = [to_plain(part) for part in asset.video.parts[:8]]
    elif asset.audio:
        meta = asset.audio.meta
    elif asset.image:
        meta = asset.image.meta
    if asset.audio and asset.audio.music:
        music_parts = [to_plain(part) for part in asset.audio.music.parts[:6]]
    if asset.audio and asset.audio.asr:
        asr_parts = [to_plain(part) for part in asset.audio.asr.parts[:6]]

    row: dict[str, Any] = {
        "id": asset.id,
        "role": asset.role,
        "kind": asset.kind.value if isinstance(asset.kind, MediaKind) else str(asset.kind),
        "name": Path(asset.path).name,
        "duration": getattr(meta, "duration", None) if meta else None,
        "width": getattr(meta, "width", None) if meta else None,
        "height": getattr(meta, "height", None) if meta else None,
        "has_audio": getattr(meta, "has_audio", False) if meta else False,
        "has_video": getattr(meta, "has_video", False) if meta else False,
        "video_parts": video_parts,
        "music_parts": music_parts,
        "asr_parts": asr_parts,
        "notes": list(asset.notes or []),
    }
    if asset.image:
        row["image_description"] = asset.image.description
        row["image_visual_style"] = asset.image.visual_style
        row["image_suggested_use"] = asset.image.suggested_use
    return row


def _summary_fallback(struct_info: str, source_name: str) -> str:
    for line in (struct_info or "").splitlines():
        text = re.sub(r"[*#`>\-]+", "", line).strip()
        if len(text) >= 4 and "未能生成" not in text:
            return text[:40]
    name = Path(source_name or "样例视频").stem
    return f"{name[:24]}结构参考"
