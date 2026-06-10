from __future__ import annotations

import json

from backend.ark import ArkClient


class _FakeResponse:
    ok = True
    content = b'{"output_text":"\\u4f60\\u597d","id":"resp_1"}'
    text = content.decode("utf-8")

    def json(self):
        return json.loads(self.content)


def test_ark_response_text_writes_raw_request_and_response_bodies(tmp_path, monkeypatch):
    captured: dict[str, object] = {}

    def fake_post(url, *, headers, data, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr("backend.ark.requests.post", fake_post)

    client = ArkClient("key", "model", timeout=12, raw_log_dir=tmp_path)
    raw, data = client.text("你好", instructions="系统提示")

    request_logs = sorted(tmp_path.glob("*.request.raw"))
    response_logs = sorted(tmp_path.glob("*.response.raw"))
    assert len(request_logs) == 1
    assert len(response_logs) == 1
    assert request_logs[0].read_bytes() == captured["data"]
    assert response_logs[0].read_text(encoding="utf-8") == '{"output_text": "你好", "id": "resp_1"}'

    request_body = json.loads(request_logs[0].read_text(encoding="utf-8"))
    assert request_body["model"] == "model"
    assert request_body["instructions"] == "系统提示"
    assert request_body["input"][0]["content"][0]["text"] == "你好"
    assert "\\u4f60" not in request_logs[0].read_text(encoding="utf-8")
    assert raw == "你好"
    assert data == {"output_text": "你好", "id": "resp_1"}
