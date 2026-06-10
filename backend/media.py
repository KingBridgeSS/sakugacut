from __future__ import annotations

import json
import math
import mimetypes
import subprocess
from pathlib import Path
from typing import Any

from .models import MediaKind, MediaMeta, MusicPart


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def detect_kind(path: str | Path) -> MediaKind:
    suffix = Path(path).suffix.lower()
    if suffix in VIDEO_EXTS:
        return MediaKind.video
    if suffix in AUDIO_EXTS:
        return MediaKind.audio
    if suffix in IMAGE_EXTS:
        return MediaKind.image
    return MediaKind.unknown


def run_cmd(args: list[str], cwd: Path | None = None, timeout: int = 120) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "cmd": args,
        }
    except Exception as exc:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(exc), "cmd": args}


def _fps(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    try:
        if "/" in value:
            a, b = value.split("/", 1)
            return float(a) / float(b)
        return float(value)
    except Exception:
        return None


def ffprobe(path: str | Path) -> MediaMeta:
    path = Path(path)
    meta = MediaMeta(
        path=str(path),
        name=path.name,
        kind=detect_kind(path),
        mime=mimetypes.guess_type(path.name)[0] or "",
        size=path.stat().st_size if path.exists() else 0,
    )
    if not path.exists():
        meta.errors.append("file does not exist")
        return meta

    result = run_cmd(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        timeout=60,
    )
    if not result["ok"]:
        meta.errors.append(result["stderr"] or "ffprobe failed")
        return meta

    try:
        probe = json.loads(result["stdout"] or "{}")
    except json.JSONDecodeError as exc:
        meta.errors.append(f"ffprobe json parse failed: {exc}")
        return meta

    meta.probe = probe
    fmt = probe.get("format") or {}
    try:
        meta.duration = float(fmt.get("duration")) if fmt.get("duration") else None
    except Exception:
        meta.duration = None

    for stream in probe.get("streams") or []:
        codec_type = stream.get("codec_type")
        if codec_type == "video":
            meta.has_video = True
            meta.width = stream.get("width") or meta.width
            meta.height = stream.get("height") or meta.height
            meta.fps = _fps(stream.get("avg_frame_rate") or stream.get("r_frame_rate")) or meta.fps
            if meta.duration is None and stream.get("duration"):
                try:
                    meta.duration = float(stream["duration"])
                except Exception:
                    pass
        if codec_type == "audio":
            meta.has_audio = True
            if meta.duration is None and stream.get("duration"):
                try:
                    meta.duration = float(stream["duration"])
                except Exception:
                    pass
    return meta


def extract_audio(video_path: str | Path, out_dir: str | Path) -> tuple[Path | None, str]:
    video_path = Path(video_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{video_path.stem}_audio.wav"
    result = run_cmd(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(out_path),
        ],
        timeout=180,
    )
    if result["ok"] and out_path.exists():
        return out_path, result["stderr"]
    return None, result["stderr"] or "audio extraction failed"


def heuristic_music_parts(meta: MediaMeta) -> list[MusicPart]:
    duration = meta.duration or 9.0
    count = max(1, min(6, math.ceil(duration / 3.0)))
    step = duration / count
    return [
        MusicPart(
            start_time=round(i * step, 2),
            end_time=round(duration if i == count - 1 else (i + 1) * step, 2),
            description=f"audio energy section {i + 1}",
        )
        for i in range(count)
    ]
