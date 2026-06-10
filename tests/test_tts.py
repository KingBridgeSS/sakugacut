from __future__ import annotations

import base64

from backend.tts import _iter_json_events


class FakeResponse:
    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks

    def iter_content(self, chunk_size: int = 8192):
        yield from self._chunks


def test_iter_json_events_parses_concatenated_chunked_objects():
    audio = base64.b64encode(b"abc").decode("ascii")
    payload = f'{{"code":0,"message":"","data":"{audio}"}}{{"code":20000000,"message":"ok","data":null}}'

    events = list(_iter_json_events(FakeResponse([payload[:9].encode(), payload[9:31].encode(), payload[31:].encode()])))

    assert [event["code"] for event in events] == [0, 20000000]
    assert base64.b64decode(events[0]["data"]) == b"abc"


def test_iter_json_events_parses_sse_data_lines():
    audio = base64.b64encode(b"xyz").decode("ascii")
    payload = f'data: {{"code":0,"message":"","data":"{audio}"}}\n\n'

    events = list(_iter_json_events(FakeResponse([payload.encode()])))

    assert len(events) == 1
    assert base64.b64decode(events[0]["data"]) == b"xyz"
