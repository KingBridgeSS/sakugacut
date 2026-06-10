from __future__ import annotations

import base64
import json
import uuid
from pathlib import Path
from typing import Any, Iterator

import requests

from .config import settings


class DoubaoTTSError(RuntimeError):
    pass


class DoubaoTTSClient:
    def __init__(self, timeout: int = 180):
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(settings.doubao_speech_key)

    def synthesize(
        self,
        text: str,
        output_path: str | Path,
        *,
        speaker: str | None = None,
        resource_id: str | None = None,
        speech_rate: int = 0,
        loudness_rate: int = 0,
        sample_rate: int | None = None,
    ) -> dict[str, Any]:
        text = " ".join(str(text or "").split())
        if not text:
            raise DoubaoTTSError("TTS text is empty")
        if not self.enabled:
            raise DoubaoTTSError("DOUBAO_SPEECH_KEY is not configured")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        speaker = speaker or settings.doubao_tts_speaker
        resource_id = resource_id or settings.doubao_tts_resource_id
        request_id = str(uuid.uuid4())
        payload = {
            "user": {"uid": "sakugacut"},
            "req_params": {
                "text": text,
                "speaker": speaker,
                "audio_params": {
                    "format": "mp3",
                    "sample_rate": int(sample_rate or settings.doubao_tts_sample_rate),
                    "speech_rate": int(speech_rate),
                    "loudness_rate": int(loudness_rate),
                },
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "X-Api-Key": settings.doubao_speech_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": request_id,
        }

        with requests.post(
            settings.doubao_tts_url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=self.timeout,
        ) as resp:
            logid = resp.headers.get("X-Tt-Logid", "")
            if not resp.ok:
                raise DoubaoTTSError(f"Doubao TTS HTTP {resp.status_code}: {resp.text[:800]} logid={logid}")

            audio_parts: list[bytes] = []
            final_event: dict[str, Any] | None = None
            for event in _iter_json_events(resp):
                final_event = event
                code = _event_code(event.get("code"))
                if code not in (None, 0, 20000000):
                    raise DoubaoTTSError(f"Doubao TTS failed code={code}: {event.get('message', '')} logid={logid}")
                data = event.get("data")
                if isinstance(data, str) and data:
                    try:
                        audio_parts.append(base64.b64decode(data))
                    except Exception as exc:
                        raise DoubaoTTSError(f"Doubao TTS returned invalid base64 audio: {exc} logid={logid}") from exc

        if not audio_parts:
            raise DoubaoTTSError(f"Doubao TTS returned no audio data: {final_event or {}}")

        audio = b"".join(audio_parts)
        output_path.write_bytes(audio)
        return {
            "path": str(output_path),
            "bytes": len(audio),
            "speaker": speaker,
            "resource_id": resource_id,
            "request_id": request_id,
            "logid": logid,
        }


def _iter_json_events(resp: requests.Response) -> Iterator[dict[str, Any]]:
    decoder = json.JSONDecoder()
    buffer = ""
    for chunk in resp.iter_content(chunk_size=8192):
        if not chunk:
            continue
        buffer += chunk.decode("utf-8", errors="replace")
        while True:
            buffer = buffer.lstrip()
            if not buffer:
                break
            if buffer.startswith("data:"):
                line, sep, rest = buffer.partition("\n")
                if not sep:
                    break
                buffer = rest
                payload = line.removeprefix("data:").strip()
                if payload and payload != "[DONE]":
                    yield json.loads(payload)
                continue
            try:
                event, index = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                break
            buffer = buffer[index:]
            if isinstance(event, dict):
                yield event

    if buffer.strip():
        for line in buffer.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line.removeprefix("data:").strip()
            if line and line != "[DONE]":
                yield json.loads(line)


def _event_code(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return -1
