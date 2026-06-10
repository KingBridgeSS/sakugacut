from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class JsonModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class MediaKind(str, Enum):
    video = "video"
    audio = "audio"
    image = "image"
    unknown = "unknown"


class MediaMeta(JsonModel):
    path: str
    name: str
    kind: MediaKind
    mime: str = ""
    size: int = 0
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    has_audio: bool = False
    has_video: bool = False
    probe: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class VideoPart(JsonModel):
    model_config = ConfigDict(extra="ignore")

    start_time: float = 0.0
    end_time: float = 0.0
    description: str = ""


class MusicPart(JsonModel):
    model_config = ConfigDict(extra="ignore")

    start_time: float = 0.0
    end_time: float = 0.0
    description: str = ""


class ASRPart(JsonModel):
    model_config = ConfigDict(extra="ignore")

    start_time: float = 0.0
    end_time: float = 0.0
    text: str = ""


class MusicIR(JsonModel):
    model_config = ConfigDict(extra="ignore")

    parts: list[MusicPart] = Field(default_factory=list)


class ASRIR(JsonModel):
    model_config = ConfigDict(extra="ignore")

    parts: list[ASRPart] = Field(default_factory=list)


class VideoIR(JsonModel):
    model_config = ConfigDict(extra="ignore")

    meta: MediaMeta
    parts: list[VideoPart] = Field(default_factory=list)


class AudioIR(JsonModel):
    meta: MediaMeta
    music: MusicIR | None = None
    asr: ASRIR | None = None
    errors: list[str] = Field(default_factory=list)


class ImageIR(JsonModel):
    meta: MediaMeta
    description: str = ""
    objects: list[str] = Field(default_factory=list)
    visual_style: str = ""
    suggested_use: str = ""
    raw_llm: str = ""
    llm_json: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)


class AssetIR(JsonModel):
    id: str
    role: Literal["sample", "asset"] = "asset"
    path: str
    kind: MediaKind
    video: VideoIR | None = None
    audio: AudioIR | None = None
    image: ImageIR | None = None
    notes: list[str] = Field(default_factory=list)


class AnalysisBundle(JsonModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    target_requirement: str = ""
    struct_info: str = ""
    samples: list[AssetIR] = Field(default_factory=list)
    assets: list[AssetIR] = Field(default_factory=list)
    knowledge_profile_ids: list[str] = Field(default_factory=list)
    selected_knowledge_profile_ids: list[str] = Field(default_factory=list)
    knowledge_selection_reason: str = ""
    notes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class TimelineSlot(JsonModel):
    id: str
    start_time: float
    end_time: float
    source_asset_id: str | None = None
    source_path: str | None = None
    media_start: float = 0.0
    playback_rate: float = 1.0
    role: str = ""
    onscreen_text: str = ""
    visual_fallback_text: str = ""
    narration: str = ""
    transition: str = "cut"
    notes: str = ""


class TimelinePlan(JsonModel):
    title: str = "SakugaCut Demo"
    format: Literal["vertical", "horizontal"] = "vertical"
    width: int = 1080
    height: int = 1920
    duration: float = 12.0
    slots: list[TimelineSlot] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    packaging: dict[str, Any] = Field(default_factory=dict)
    audio_strategy: Any = Field(default_factory=dict)
    explanation: str = ""
    missing_assets: list[str] = Field(default_factory=list)
    raw_agent: str = ""


class ToolCall(JsonModel):
    id: str = ""
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(JsonModel):
    id: str = ""
    name: str
    ok: bool = False
    output: str = ""
    artifacts: dict[str, str] = Field(default_factory=dict)
    error: str = ""


class JobState(str, Enum):
    created = "created"
    phase1_running = "phase1_running"
    phase1_done = "phase1_done"
    phase2_running = "phase2_running"
    done = "done"
    error = "error"


class JobStatus(JsonModel):
    job_id: str
    state: JobState = JobState.created
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    progress: list[str] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    error: str | None = None
