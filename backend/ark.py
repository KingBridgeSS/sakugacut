from __future__ import annotations

import base64
import json
import mimetypes
import time
import uuid
from pathlib import Path
from typing import Any

import requests

from .config import settings


class ArkError(RuntimeError):
    pass


class ArkClient:
    def __init__(self, api_key: str, model: str, timeout: int = 240, raw_log_dir: str | Path | None = None):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = settings.ark_base_url.rstrip("/")
        self.raw_log_dir = Path(raw_log_dir) if raw_log_dir is not None else settings.llm_raw_log_dir

    def set_raw_log_dir(self, raw_log_dir: str | Path | None) -> None:
        self.raw_log_dir = Path(raw_log_dir) if raw_log_dir is not None else None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def upload_file(self, path: str | Path, *, video_fps: float | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise ArkError("Ark API key/model is not configured")
        path = Path(path)
        data = {"purpose": "user_data"}
        if video_fps is not None:
            data["preprocess_configs[video][fps]"] = str(video_fps)
        with path.open("rb") as fh:
            resp = requests.post(
                f"{self.base_url}/files",
                headers=self.headers,
                data=data,
                files={"file": (path.name, fh)},
                timeout=self.timeout,
            )
        self._raise(resp)
        info = resp.json()
        file_id = info.get("id")
        if not file_id:
            raise ArkError(f"file upload response missing id: {info}")

        deadline = time.time() + self.timeout
        while info.get("status") == "processing" and time.time() < deadline:
            time.sleep(2)
            resp = requests.get(f"{self.base_url}/files/{file_id}", headers=self.headers, timeout=30)
            self._raise(resp)
            info = resp.json()
        if info.get("status") in {"failed", "error"}:
            raise ArkError(f"file processing failed: {info}")
        return info

    def response_text(
        self,
        content: list[dict[str, Any]],
        *,
        instructions: str | None = None,
        model: str | None = None,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        max_tool_calls: int | None = None,
        parallel_tool_calls: bool | None = None,
    ) -> tuple[str, dict[str, Any]]:
        if not self.enabled:
            raise ArkError("Ark API key/model is not configured")
        payload: dict[str, Any] = {
            "model": model or self.model,
            "input": [{"type": "message", "role": "user", "content": content}],
        }
        if instructions:
            payload["instructions"] = instructions
        if response_format:
            payload["text"] = {"format": response_format}
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if max_tool_calls is not None:
            payload["max_tool_calls"] = max_tool_calls
        # parallel_tool_calls 目前未启用，作为保留字段
        if parallel_tool_calls is not None:
            payload["parallel_tool_calls"] = parallel_tool_calls
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        request_log, response_log = self._raw_log_paths()
        self._write_raw_log(request_log, body)
        resp = requests.post(
            f"{self.base_url}/responses",
            headers={**self.headers, "Content-Type": "application/json"},
            data=body,
            timeout=self.timeout,
        )
        self._write_raw_log(response_log, readable_raw_log_bytes(resp.content))
        self._raise(resp)
        data = resp.json()
        return extract_response_text(data), data

    def _raw_log_paths(self) -> tuple[Path, Path]:
        root = self.raw_log_dir
        if root is None:
            raise ArkError("LLM raw log dir is not configured")
        root.mkdir(parents=True, exist_ok=True)
        stem = f"{time.time_ns()}-{uuid.uuid4().hex[:8]}"
        return root / f"{stem}.request.raw", root / f"{stem}.response.raw"

    @staticmethod
    def _write_raw_log(path: Path, data: bytes) -> None:
        path.write_bytes(data)

    def text(
        self,
        prompt: str,
        *,
        instructions: str | None = None,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        max_tool_calls: int | None = None,
        parallel_tool_calls: bool | None = None,
    ) -> tuple[str, dict[str, Any]]:
        return self.response_text(
            [{"type": "input_text", "text": prompt}],
            instructions=instructions,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            max_tool_calls=max_tool_calls,
            parallel_tool_calls=parallel_tool_calls,
        )

    def video(
        self,
        path: str | Path,
        prompt: str,
        *,
        instructions: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        file_info = self.upload_file(path, video_fps=5)
        return self.response_text(
            [
                {"type": "input_video", "file_id": file_info["id"]},
                {"type": "input_text", "text": prompt},
            ],
            instructions=instructions,
            response_format=response_format,
        )

    def audio(
        self,
        path: str | Path,
        prompt: str,
        *,
        instructions: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        file_info = self.upload_file(path)
        return self.response_text(
            [
                {"type": "input_audio", "file_id": file_info["id"]},
                {"type": "input_text", "text": prompt},
            ],
            instructions=instructions,
            response_format=response_format,
        )

    def image(
        self,
        path: str | Path,
        prompt: str,
        *,
        instructions: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        data_url = file_data_url(path)
        return self.response_text(
            [
                {"type": "input_image", "image_url": data_url},
                {"type": "input_text", "text": prompt},
            ],
            instructions=instructions,
            response_format=response_format,
        )

    @staticmethod
    def _raise(resp: requests.Response) -> None:
        if resp.ok:
            return
        body = resp.text[:1200]
        raise ArkError(f"Ark HTTP {resp.status_code}: {body}")


def pro_client(timeout: int | None = None, *, raw_log_dir: str | Path | None = None) -> ArkClient:
    return ArkClient(settings.ark_api_key, settings.ark_model, timeout or settings.phase1_timeout, raw_log_dir=raw_log_dir)


def lite_client(timeout: int | None = None, *, raw_log_dir: str | Path | None = None) -> ArkClient:
    return ArkClient(settings.ark_lite_api_key, settings.ark_lite_model, timeout or settings.phase1_timeout, raw_log_dir=raw_log_dir)


def readable_raw_log_bytes(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8")
        parsed = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return data
    return json.dumps(parsed, ensure_ascii=False).encode("utf-8")


def file_data_url(path: str | Path) -> str:
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{data}"


def json_schema_format(name: str, schema: dict[str, Any], *, strict: bool = True) -> dict[str, Any]:
    return {"type": "json_schema", "name": name, "strict": strict, "schema": schema}


def json_object_format() -> dict[str, str]:
    return {"type": "json_object"}


def extract_response_text(data: Any) -> str:
    if isinstance(data, dict) and isinstance(data.get("output_text"), str):
        return data["output_text"]

    texts: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            typ = value.get("type")
            if typ in {"output_text", "text"} and isinstance(value.get("text"), str):
                texts.append(value["text"])
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(data)
    if texts:
        return "\n".join(dict.fromkeys(texts))

    fallback: list[str] = []

    def collect_strings(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"id", "model", "status", "type", "role"}:
                    continue
                collect_strings(item)
        elif isinstance(value, list):
            for item in value:
                collect_strings(item)
        elif isinstance(value, str) and len(value.strip()) > 2:
            fallback.append(value.strip())

    collect_strings(data)
    return "\n".join(fallback[:3])


def extract_response_tool_calls(data: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add_call(call_id: Any, name: Any, arguments: Any) -> None:
        if not name:
            return
        args = parse_tool_arguments(arguments)
        call_key = (str(call_id or ""), str(name), json.dumps(args, ensure_ascii=False, sort_keys=True))
        if call_key in seen:
            return
        seen.add(call_key)
        calls.append({"id": str(call_id or ""), "name": str(name), "arguments": args})

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("type") == "function_call" and value.get("name"):
                add_call(value.get("call_id") or value.get("id"), value.get("name"), value.get("arguments"))
            raw_calls = value.get("tool_calls")
            if isinstance(raw_calls, list):
                for item in raw_calls:
                    if not isinstance(item, dict):
                        continue
                    function = item.get("function") if isinstance(item.get("function"), dict) else {}
                    add_call(item.get("id"), function.get("name") or item.get("name"), function.get("arguments") or item.get("arguments"))
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(data)
    return calls


def parse_tool_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"command": text}
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    return {"value": value}
