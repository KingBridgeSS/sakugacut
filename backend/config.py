from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


class Settings:
    root: Path = ROOT
    runs_dir: Path = ROOT / "runs"
    knowledge_dir: Path = ROOT / "knowledge_profiles"
    ark_base_url: str = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    ark_api_key: str = os.getenv("ARK_API_KEY", "")
    ark_model: str = os.getenv("ARK_MODEL", "")
    ark_lite_api_key: str = os.getenv("ARK_LITE_API_KEY", os.getenv("ARK_API_KEY", ""))
    ark_lite_model: str = os.getenv("ARK_LITE_MODEL", "")
    llm_raw_log_dir: Path = Path(os.getenv("SAKUGACUT_LLM_RAW_LOG_DIR", str(ROOT / "llm_raw")))
    doubao_speech_key: str = os.getenv("DOUBAO_SPEECH_KEY", "")
    doubao_tts_url: str = os.getenv("DOUBAO_TTS_URL", "https://openspeech.bytedance.com/api/v3/tts/unidirectional")
    doubao_tts_resource_id: str = os.getenv("DOUBAO_TTS_RESOURCE_ID", "seed-tts-2.0")
    doubao_tts_speaker: str = os.getenv("DOUBAO_TTS_SPEAKER", "zh_female_vv_uranus_bigtts")
    doubao_tts_sample_rate: int = int(os.getenv("DOUBAO_TTS_SAMPLE_RATE", "24000"))
    hyperframes_package: str = os.getenv("SAKUGACUT_HYPERFRAMES_PACKAGE", "hyperframes")
    phase1_timeout: int = int(os.getenv("SAKUGACUT_PHASE1_TIMEOUT", "240"))
    agent_timeout: int = int(os.getenv("SAKUGACUT_AGENT_TIMEOUT", "240"))
    render_timeout: int = int(os.getenv("SAKUGACUT_RENDER_TIMEOUT", "600"))
    max_agent_steps: int = int(os.getenv("SAKUGACUT_AGENT_STEPS", "32"))
    hyperframes_agent_steps: int = int(os.getenv("SAKUGACUT_HYPERFRAMES_AGENT_STEPS", "32"))


settings = Settings()
settings.runs_dir.mkdir(parents=True, exist_ok=True)
settings.knowledge_dir.mkdir(parents=True, exist_ok=True)
