from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .ark import ArkError, json_schema_format, lite_client, pro_client
from .json_utils import extract_json, read_json, to_plain, write_json
from .media import detect_kind, extract_audio, ffprobe, heuristic_music_parts
from .models import (
    ASRIR,
    ASRPart,
    AnalysisBundle,
    AssetIR,
    AudioIR,
    ImageIR,
    MediaKind,
    MusicIR,
    MusicPart,
    VideoIR,
    VideoPart,
)
from .storage import add_artifact, add_progress


# 多模态分析提示词：分别约束视频、音乐/音效、ASR、图片和样例结构总结的输出重点。
VIDEO_PROMPT = """你是短视频结构分析师。分析这个视频的创作结构，而不是复述剧情。
把视频拆成若干可迁移的片段。start_time 和 end_time 使用秒，统一保留小数点后一位。
description 写清画面、动作、节奏作用和可迁移的剪辑意图，如果出现字幕内容请描述它所在的位置。你需要尽可能多地分段，颗粒度细化一些。"""

MUSIC_PROMPT = """你是短视频声音设计师。分析音频里的音乐、音效、节奏和情绪，不要重点转写人声。
把声音拆成若干可迁移的节奏片段。start_time 和 end_time 使用秒，统一保留小数点后一位。"""

ASR_INSTRUCTIONS = """你是 ASR 专家。识别音频中的语音；若没有可识别人声，返回空 parts。"""

ASR_PROMPT = """请语音转写这段音频，并尽量给出句级时间戳。start_time 和 end_time 使用秒，统一保留小数点后一位。"""

IMAGE_PROMPT = """你是短视频素材编导。分析这张图片能在短视频结构迁移中承担什么角色。"""

STRUCT_INFO_INSTRUCTIONS = """你是短视频样例结构复盘专家。
你总结视频，后生成一个struct_info。
struct_info 必须是一个可直接交给剪辑 agent 参考的中文字符串，按以下三个小节组织：
- **脚本/段落结构**：如开头 hook、中段展开、结尾 CTA
- **包装结构**：如字幕密度、标题条、贴纸、转场、封面风格
- **背景音乐结构/描述**：如果有音乐，说说视频中音乐的结构/描述
如果某项无法从输入判断，明确写“未从样例中识别到”，不要编造。"""


# 统一片段 schema：强制 LLM 返回可解析的时间段列表，后续会转成内部 IR 模型。
PART_SCHEMA = {
    "type": "object",
    "properties": {
        "start_time": {"type": "number", "description": "片段开始时间，单位秒，保留小数点后一位。"},
        "end_time": {"type": "number", "description": "片段结束时间，单位秒，保留小数点后一位。"},
        "description": {"type": "string", "description": "片段内容和可迁移作用。"},
    },
    "required": ["start_time", "end_time", "description"],
    "additionalProperties": False,
}

VIDEO_RESPONSE_FORMAT = json_schema_format(
    "video_ir",
    {
        "type": "object",
        "properties": {
            "parts": {"type": "array", "items": PART_SCHEMA, "description": "视频片段列表。"},
        },
        "required": ["parts"],
        "additionalProperties": False,
    },
)

MUSIC_RESPONSE_FORMAT = json_schema_format(
    "music_ir",
    {
        "type": "object",
        "properties": {
            "parts": {"type": "array", "items": PART_SCHEMA, "description": "音乐或声音片段列表。"},
        },
        "required": ["parts"],
        "additionalProperties": False,
    },
)

ASR_RESPONSE_FORMAT = json_schema_format(
    "asr_ir",
    {
        "type": "object",
        "properties": {
            "parts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "start_time": {"type": "number", "description": "语音开始时间，单位秒，保留小数点后一位。"},
                        "end_time": {"type": "number", "description": "语音结束时间，单位秒，保留小数点后一位。"},
                        "text": {"type": "string", "description": "转写文本。"},
                    },
                    "required": ["start_time", "end_time", "text"],
                    "additionalProperties": False,
                },
                "description": "句级语音片段。无可识别人声时为空数组。",
            },
        },
        "required": ["parts"],
        "additionalProperties": False,
    },
)

IMAGE_RESPONSE_FORMAT = json_schema_format(
    "image_ir",
    {
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "图片内容摘要。"},
            "objects": {"type": "array", "items": {"type": "string"}, "description": "主要人物、物体或场景元素。"},
            "visual_style": {"type": "string", "description": "光线、色彩、构图和质感。"},
            "suggested_use": {
                "type": "string",
                "description": "建议用途，如 hook、proof、product、detail、background、cta。",
            },
        },
        "required": ["description", "objects", "visual_style", "suggested_use"],
        "additionalProperties": False,
    },
)

STRUCT_INFO_RESPONSE_FORMAT = json_schema_format(
    "sample_struct_info",
    {
        "type": "object",
        "properties": {
            "struct_info": {
                "type": "string",
                "description": "对样例视频脚本、包装、背景音乐结构的中文总结，保留 markdown 小节标题。",
            },
        },
        "required": ["struct_info"],
        "additionalProperties": False,
    },
)


# Phase1 负责把输入 manifest 中的样例和用户素材分析成稳定的 AnalysisBundle，供后续阶段使用。
class Phase1Analyzer:
    def __init__(self):
        self.pro = pro_client()
        self.lite = lite_client()

    def set_raw_log_dir(self, raw_log_dir: Path) -> None:
        for client in (self.pro, self.lite):
            setter = getattr(client, "set_raw_log_dir", None)
            if callable(setter):
                setter(raw_log_dir)

    def run(self, job_id: str, job_dir: Path) -> AnalysisBundle:
        self.set_raw_log_dir(job_dir / "llm_raw")
        # manifest 是 phase1 的输入契约：包含目标要求、样例素材和待处理素材路径。
        manifest = read_json(job_dir / "manifest.json", {})
        target_requirement = _target_requirement_from_manifest(manifest)
        knowledge_profile_ids = _knowledge_profile_ids_from_manifest(manifest)

        # 先分析样例素材；样例用于提炼可迁移的脚本、包装和音乐结构。
        sample_paths = _sample_paths_from_manifest(manifest)
        samples: list[AssetIR] = []
        for idx, path in enumerate(sample_paths):
            asset_id = f"sample_{idx + 1}"
            add_progress(job_id, f"phase1: analyze sample {path.name}")
            samples.append(self._analyze_asset(asset_id, "sample", path, job_dir))

        struct_info = ""
        if samples:
            add_progress(job_id, "phase1: summarize sample struct_info")
            struct_info = self.sample_struct_info(samples)

        # 再分析用户素材；这些素材会和样例结构一起交给后续生成/剪辑阶段。
        assets: list[AssetIR] = []
        for idx, item in enumerate(manifest.get("asset_paths") or []):
            path = Path(item)
            add_progress(job_id, f"phase1: analyze asset {path.name}")
            assets.append(self._analyze_asset(f"asset_{idx + 1}", "asset", path, job_dir))

        # AnalysisBundle 是跨阶段的稳定产物，写盘后同时登记为 job artifact。
        bundle = AnalysisBundle(
            job_id=job_id,
            target_requirement=target_requirement,
            struct_info=struct_info,
            samples=samples,
            assets=assets,
            knowledge_profile_ids=knowledge_profile_ids,
        )
        write_json(job_dir / "analysis.json", bundle)
        add_artifact(job_id, "analysis", "analysis.json")
        return bundle

    def _analyze_asset(self, asset_id: str, role: str, path: Path, job_dir: Path) -> AssetIR:
        # role: sample|asset
        # 按媒体类型分流；视频会先分析画面，再抽取音频复用声音/语音分析流程。
        kind = detect_kind(path)
        if kind == MediaKind.video:
            video = self._video_ir(path)
            audio, notes = self._video_audio_ir(path, job_dir, video.meta)
            return AssetIR(id=asset_id, role=role, path=str(path), kind=kind, video=video, audio=audio, notes=notes)
        if kind == MediaKind.audio:
            return AssetIR(id=asset_id, role=role, path=str(path), kind=kind, audio=self._audio_ir(path))
        if kind == MediaKind.image:
            return AssetIR(id=asset_id, role=role, path=str(path), kind=kind, image=self._image_ir(path))
        meta = ffprobe(path)
        # 不支持的媒体也返回 AssetIR，避免整个任务因为单个素材中断。
        return AssetIR(id=asset_id, role=role, path=str(path), kind=kind, notes=[f"unsupported media type: {meta.mime}"])

    def _video_ir(self, path: Path) -> VideoIR:
        meta = ffprobe(path)
        data: dict[str, Any] | None = None
        llm_error = ""
        try:
            # 优先让视觉模型拆解可迁移的视频片段。
            raw, _ = self.pro.video(path, VIDEO_PROMPT, response_format=VIDEO_RESPONSE_FORMAT)
            parsed = extract_json(raw)
            data = parsed if isinstance(parsed, dict) else None
        except Exception as exc:
            llm_error = str(exc)
            data = None

        parts = _video_parts_from_json(data, meta.duration) if data else []
        if not parts:
            reason = f": {llm_error}" if llm_error else ""
            raise RuntimeError(f"video LLM returned no valid parts for {path.name}{reason}")

        return VideoIR(meta=meta, parts=parts)

    def _video_audio_ir(self, path: Path, job_dir: Path, meta: Any) -> tuple[AudioIR | None, list[str]]:
        # 只有视频确实包含音轨时才抽音频，避免无声视频产生无意义的失败日志。
        if not getattr(meta, "has_audio", False):
            return None, []
        audio_path, audio_log = extract_audio(path, job_dir / "audio")
        if not audio_path:
            return None, [f"extract audio failed: {audio_log[:500]}"]
        audio_ir = self._audio_ir(audio_path)
        has_speech = bool(audio_ir.asr and any(part.text.strip() for part in audio_ir.asr.parts))
        has_sound_segments = bool(audio_ir.music and audio_ir.music.parts)
        notes = [f"extracted_audio_path={audio_path}"]
        # music.parts 是声音/节奏分段，可能来自兜底启发式，不等同于真实 BGM 检测。
        if has_speech:
            notes.append("audio_profile=speech_present")
        elif has_sound_segments:
            notes.append("audio_profile=non_speech_audio")
        else:
            notes.append("audio_profile=audio_track_unclassified")
        return audio_ir, notes

    def sample_struct_info(self, samples: list[AssetIR]) -> str:
        # 只基于样例 IR 总结 struct_info，不混入用户素材，避免提前替成片做决策。
        payload = {
            "samples": [_sample_payload(sample) for sample in samples],
            "task": "请基于这些样例视频分析结果生成 struct_info 字符串。",
        }
        try:
            raw, _ = self.pro.text(
                json.dumps(payload, ensure_ascii=False),
                instructions=STRUCT_INFO_INSTRUCTIONS,
                response_format=STRUCT_INFO_RESPONSE_FORMAT,
            )
            parsed = extract_json(raw)
            if isinstance(parsed, dict) and str(parsed.get("struct_info") or "").strip():
                return str(parsed["struct_info"]).strip()
        except Exception as exc:
            return f"LLM 未能生成 struct_info：{exc}"
        return ""

    def _audio_ir(self, path: Path) -> AudioIR:
        meta = ffprobe(path)
        # 音频同时拆成音乐/节奏片段和 ASR 语音片段，两类信息在后续剪辑中互补。
        return AudioIR(meta=meta, music=self._music_ir(path), asr=self._asr_ir(path))

    def _music_ir(self, path: Path) -> MusicIR:
        meta = ffprobe(path)
        raw = ""
        data: dict[str, Any] | None = None
        try:
            raw, _ = self.lite.audio(path, MUSIC_PROMPT, response_format=MUSIC_RESPONSE_FORMAT)
            parsed = extract_json(raw)
            data = parsed if isinstance(parsed, dict) else None
        except Exception as exc:
            data = None

        parts = _music_parts_from_json(data, meta.duration) if data else []
        if not parts:
            # 声音模型不可用或无有效结果时，用音频时长做节奏片段兜底。
            parts = heuristic_music_parts(meta)
        return MusicIR(parts=parts)

    def _asr_ir(self, path: Path) -> ASRIR:
        raw = ""
        data: dict[str, Any] | None = None
        try:
            raw, _ = self.lite.audio(path, ASR_PROMPT, instructions=ASR_INSTRUCTIONS, response_format=ASR_RESPONSE_FORMAT)
            parsed = extract_json(raw)
            data = parsed if isinstance(parsed, dict) else None
        except ArkError as exc:
            data = None
        except Exception as exc:
            data = None

        parts = _asr_parts_from_json(data) if data else []
        if not data and raw and raw.strip().startswith("{") is False:
            # 部分 ASR 模型可能返回纯文本而不是 JSON；保留文本，时间戳用 0 占位。
            parts = [ASRPart(start_time=0.0, end_time=0.0, text=raw.strip())]
        return ASRIR(parts=parts)

    def _image_ir(self, path: Path) -> ImageIR:
        meta = ffprobe(path)
        raw = ""
        data: dict[str, Any] | None = None
        errors: list[str] = []
        try:
            # 图片分析输出内容摘要、主体元素、视觉风格和建议用途，便于后续挑选素材位置。
            raw, _ = self.pro.image(path, IMAGE_PROMPT, response_format=IMAGE_RESPONSE_FORMAT)
            parsed = extract_json(raw)
            data = parsed if isinstance(parsed, dict) else None
        except Exception as exc:
            errors.append(f"image llm fallback: {exc}")

        return ImageIR(
            meta=meta,
            description=str((data or {}).get("description") or f"image asset: {path.name}"),
            objects=_string_list((data or {}).get("objects")),
            visual_style=str((data or {}).get("visual_style") or ""),
            suggested_use=str((data or {}).get("suggested_use") or ""),
            raw_llm=raw,
            llm_json=data,
            errors=errors,
        )


def _video_parts_from_json(data: dict[str, Any] | None, duration: float | None) -> list[VideoPart]:
    # 兼容 parts/shots、start_time/start、end_time/end 等常见字段名，降低 LLM 输出抖动影响。
    parts: list[VideoPart] = []
    for idx, item in enumerate((data or {}).get("parts") or (data or {}).get("shots") or []):
        if not isinstance(item, dict):
            continue
        start = _time_value(item.get("start_time") or item.get("start") or 0)
        end = _time_value(item.get("end_time") or item.get("end") or 0)
        if end <= start:
            end = start + max(0.5, (duration or 8.0) / 6)
        parts.append(
            VideoPart(
                start_time=round(start, 1),
                end_time=round(end, 1),
                description=str(item.get("description") or item.get("event") or item.get("summary") or f"shot {idx + 1}"),
            )
        )
    return parts


def _music_parts_from_json(data: dict[str, Any] | None, duration: float | None) -> list[MusicPart]:
    # 将声音模型输出归一化成 MusicPart，并修正异常的结束时间。
    parts: list[MusicPart] = []
    for idx, item in enumerate((data or {}).get("parts") or []):
        if not isinstance(item, dict):
            continue
        start = _time_value(item.get("start_time") or item.get("start") or 0)
        end = _time_value(item.get("end_time") or item.get("end") or 0)
        if end <= start:
            end = start + max(0.5, (duration or 8.0) / 6)
        parts.append(
            MusicPart(
                start_time=round(start, 1),
                end_time=round(end, 1),
                description=str(item.get("description") or f"music part {idx + 1}"),
            )
        )
    return parts


def _asr_parts_from_json(data: dict[str, Any] | None) -> list[ASRPart]:
    # 将 ASR JSON 归一化成句级片段；空或异常项直接跳过。
    parts: list[ASRPart] = []
    for item in (data or {}).get("parts") or []:
        if not isinstance(item, dict):
            continue
        parts.append(
            ASRPart(
                start_time=round(_time_value(item.get("start_time") or item.get("start") or 0), 1),
                end_time=round(_time_value(item.get("end_time") or item.get("end") or 0), 1),
                text=str(item.get("text") or ""),
            )
        )
    return parts


def _time_value(value: Any) -> float:
    # 支持秒数、"mm:ss"、"hh:mm:ss" 等格式，解析失败统一回落到 0。
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return 0.0
    if ":" in text:
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
        if len(nums) == 3:
            return nums[0] * 3600 + nums[1] * 60 + nums[2]
        if len(nums) == 2:
            return nums[0] * 60 + nums[1]
    try:
        return float(text)
    except ValueError:
        return 0.0


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(value)]


def _sample_payload(sample: AssetIR) -> dict[str, Any]:
    # 只提取样例结构总结需要的字段，避免把完整对象直接塞给 LLM。
    return {
        "id": sample.id,
        "kind": sample.kind.value if isinstance(sample.kind, MediaKind) else str(sample.kind),
        "name": Path(sample.path).name,
        "video_meta": to_plain(sample.video.meta) if sample.video else None,
        "video_parts": [to_plain(part) for part in (sample.video.parts if sample.video else [])],
        "music_parts": [to_plain(part) for part in (sample.audio.music.parts if sample.audio and sample.audio.music else [])],
        "asr_parts": [to_plain(part) for part in (sample.audio.asr.parts if sample.audio and sample.audio.asr else [])],
        "notes": list(sample.notes or []),
    }


def _sample_paths_from_manifest(manifest: dict[str, Any]) -> list[Path]:
    raw_paths = manifest.get("sample_paths")
    if not isinstance(raw_paths, list):
        return []
    paths: list[Path] = []
    for item in raw_paths:
        text = str(item or "").strip()
        if text:
            paths.append(Path(text))
    return paths

def _target_requirement_from_manifest(manifest: dict[str, Any]) -> str:
    if isinstance(manifest.get("target_requirement"), str):
        return manifest["target_requirement"].strip()
    return ""


def _knowledge_profile_ids_from_manifest(manifest: dict[str, Any]) -> list[str]:
    value = manifest.get("knowledge_profile_ids")
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
