from __future__ import annotations

import hashlib
import io
import json

import pytest

from backend.agent import CreativeCompilerAgent, HyperframesSubAgent, SakugaCutAgent, _analysis_for_compiler, _analysis_has_tts_for_slot
from backend.app import app
from backend.config import settings
from backend.json_utils import read_json, write_json
from backend.models import (
    ASRIR,
    ASRPart,
    AnalysisBundle,
    AssetIR,
    AudioIR,
    MediaKind,
    MediaMeta,
    MusicIR,
    MusicPart,
    JobState,
    JobStatus,
    TimelinePlan,
    TimelineSlot,
    VideoIR,
    VideoPart,
)
from backend.phase1 import Phase1Analyzer


def _asset(asset_id: str, role: str, path: str = "asset.mp4", kind: MediaKind = MediaKind.video) -> AssetIR:
    return AssetIR(id=asset_id, role=role, path=path, kind=kind)


def _analyzed_video_asset(asset_id: str, role: str, path: str) -> AssetIR:
    video_meta = MediaMeta(
        path=path,
        name=path,
        kind=MediaKind.video,
        duration=12,
        width=1080,
        height=1920,
        has_audio=True,
        has_video=True,
    )
    audio_meta = MediaMeta(
        path=f"{path}.wav",
        name=f"{path}.wav",
        kind=MediaKind.audio,
        duration=12,
        has_audio=True,
    )
    return AssetIR(
        id=asset_id,
        role=role,
        path=path,
        kind=MediaKind.video,
        video=VideoIR(
            meta=video_meta,
            parts=[
                VideoPart(start_time=idx, end_time=idx + 1, description=f"sample shot {idx}")
                for idx in range(12)
            ],
        ),
        audio=AudioIR(
            meta=audio_meta,
            music=MusicIR(
                parts=[
                    MusicPart(start_time=idx, end_time=idx + 1, description=f"sample beat {idx}")
                    for idx in range(9)
                ]
            ),
            asr=ASRIR(parts=[ASRPart(start_time=idx, end_time=idx + 1, text=f"sample line {idx}") for idx in range(9)]),
        ),
        notes=["audio_profile=speech_present"],
    )


def test_create_job_accepts_multiple_samples_and_requires_assets(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path)
    settings.runs_dir.mkdir(parents=True, exist_ok=True)

    client = app.test_client()
    missing_assets = client.post(
        "/api/jobs",
        data={"samples": [(io.BytesIO(b"sample"), "sample.mp4")]},
        content_type="multipart/form-data",
    )
    assert missing_assets.status_code == 400

    old_field_response = client.post(
        "/api/jobs",
        data={
            "sample": (io.BytesIO(b"old sample"), "old.mp4"),
            "assets": [(io.BytesIO(b"a0"), "a0.mp4")],
        },
        content_type="multipart/form-data",
    )
    assert old_field_response.status_code == 200
    old_field_job_id = old_field_response.get_json()["job_id"]
    old_field_manifest = read_json(tmp_path / old_field_job_id / "manifest.json")
    assert old_field_manifest["sample_paths"] == []

    response = client.post(
        "/api/jobs",
        data={
            "samples": [(io.BytesIO(b"s1"), "s1.mp4"), (io.BytesIO(b"s2"), "s2.mp4")],
            "assets": [(io.BytesIO(b"a1"), "a1.mp4")],
            "target_requirement": "突出产品质感",
            "knowledge_profile_ids": ["profile_a", "profile_b"],
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    job_id = response.get_json()["job_id"]
    manifest = read_json(tmp_path / job_id / "manifest.json")

    assert [path.split("/")[-1] for path in manifest["sample_paths"]] == ["sample_1_s1.mp4", "sample_2_s2.mp4"]
    assert [path.split("/")[-1] for path in manifest["asset_paths"]] == ["asset_1_a1.mp4"]
    assert "topic" not in manifest
    assert manifest["target_requirement"] == "突出产品质感"
    assert manifest["knowledge_profile_ids"] == ["profile_a", "profile_b"]


def test_create_revision_job_reuses_analysis_and_starts_phase2(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path)
    settings.runs_dir.mkdir(parents=True, exist_ok=True)

    parent_dir = tmp_path / "parent"
    parent_dir.mkdir(parents=True)
    asset_path = parent_dir / "uploads" / "asset.mp4"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"asset")
    (parent_dir / "output.mp4").write_bytes(b"mp4")
    (parent_dir / "video_script.md").write_text("上一版脚本", encoding="utf-8")

    analysis = AnalysisBundle(
        job_id="parent",
        target_requirement="原始要求",
        assets=[
            _asset("asset_1", "asset", str(asset_path)),
            AssetIR(
                id="asset_tts_1",
                role="asset",
                path=str(parent_dir / "tts" / "asset_tts_1.mp3"),
                kind=MediaKind.audio,
                audio=AudioIR(meta=MediaMeta(path="tts.mp3", name="tts.mp3", kind=MediaKind.audio, has_audio=True)),
                notes=["generated_tts=true", "tts_for_slot=slot_1", "tts_text_sha1=old"],
            ),
        ],
        knowledge_profile_ids=["profile_a"],
        selected_knowledge_profile_ids=["profile_a"],
    )
    write_json(
        parent_dir / "manifest.json",
        {
            "sample_paths": [],
            "asset_paths": [str(asset_path)],
            "target_requirement": "原始要求",
            "knowledge_profile_ids": ["profile_a"],
        },
    )
    write_json(parent_dir / "analysis.json", analysis)
    write_json(parent_dir / "plan.json", {"title": "上一版", "raw_agent": "large raw text", "slots": []})
    write_json(
        parent_dir / "status.json",
        JobStatus(
            job_id="parent",
            state=JobState.done,
            artifacts={"manifest": "manifest.json", "analysis": "analysis.json", "plan": "plan.json", "output": "output.mp4"},
        ),
    )

    captured: dict[str, object] = {}

    def fake_start_thread(job_id, fn):
        captured["job_id"] = job_id
        captured["fn"] = fn

    monkeypatch.setattr("backend.app._start_thread", fake_start_thread)

    response = app.test_client().post("/api/jobs/parent/revisions", json={"instruction": "结尾 CTA 改成关注账号"})

    assert response.status_code == 200
    payload = response.get_json()
    child_id = payload["job_id"]
    assert captured["job_id"] == child_id
    assert payload["parent_job_id"] == "parent"
    assert payload["base_job_id"] == "parent"
    assert payload["revision_instruction"] == "结尾 CTA 改成关注账号"
    assert payload["revision_index"] == 1
    assert "revision_context" in payload["artifacts"]

    child_manifest = read_json(tmp_path / child_id / "manifest.json")
    assert child_manifest["parent_job_id"] == "parent"
    assert child_manifest["base_job_id"] == "parent"
    assert child_manifest["revision_instruction"] == "结尾 CTA 改成关注账号"
    assert child_manifest["asset_paths"] == [str(asset_path)]

    child_analysis = read_json(tmp_path / child_id / "analysis.json")
    assert child_analysis["job_id"] == child_id
    assert [asset["id"] for asset in child_analysis["assets"]] == ["asset_1"]

    context = read_json(tmp_path / child_id / "revision_context.json")
    assert context["instruction"] == "结尾 CTA 改成关注账号"
    assert context["previous"]["job_id"] == "parent"
    assert context["previous"]["plan"]["title"] == "上一版"
    assert context["previous"]["video_script"] == "上一版脚本"


def test_create_revision_rejects_invalid_parent_state(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path)
    settings.runs_dir.mkdir(parents=True, exist_ok=True)

    parent_dir = tmp_path / "parent"
    parent_dir.mkdir(parents=True)
    write_json(parent_dir / "status.json", JobStatus(job_id="parent", state=JobState.created))

    client = app.test_client()
    assert client.post("/api/jobs/parent/revisions", json={"instruction": ""}).status_code == 400
    response = client.post("/api/jobs/parent/revisions", json={"instruction": "改 CTA"})
    assert response.status_code == 400
    assert "must be done" in response.get_json()["error"]


def test_phase1_writes_samples_array_and_supports_no_samples(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path)
    settings.runs_dir.mkdir(parents=True, exist_ok=True)

    def fake_analyze(self, asset_id, role, path, job_dir):
        return _asset(asset_id, role, str(path))

    def fake_struct(self, samples):
        return "combined struct: " + ",".join(sample.id for sample in samples)

    monkeypatch.setattr(Phase1Analyzer, "_analyze_asset", fake_analyze)
    monkeypatch.setattr(Phase1Analyzer, "sample_struct_info", fake_struct)

    single_dir = tmp_path / "single"
    write_json(
        single_dir / "manifest.json",
        {
            "sample_paths": [str(single_dir / "s1.mp4")],
            "asset_paths": [str(single_dir / "a1.mp4")],
            "target_requirement": "单样例",
        },
    )
    Phase1Analyzer().run("single", single_dir)
    single = read_json(single_dir / "analysis.json")
    assert [sample["id"] for sample in single["samples"]] == ["sample_1"]
    assert single["struct_info"] == "combined struct: sample_1"
    assert "topic" not in single

    multi_dir = tmp_path / "multi"
    write_json(
        multi_dir / "manifest.json",
        {
            "sample_paths": [str(multi_dir / "s1.mp4"), str(multi_dir / "s2.mp4")],
            "asset_paths": [str(multi_dir / "a1.mp4")],
            "target_requirement": "更快节奏",
        },
    )
    Phase1Analyzer().run("multi", multi_dir)
    multi = read_json(multi_dir / "analysis.json")
    assert "sample" not in multi
    assert [sample["id"] for sample in multi["samples"]] == ["sample_1", "sample_2"]
    assert multi["struct_info"] == "combined struct: sample_1,sample_2"
    assert multi["target_requirement"] == "更快节奏"
    assert "topic" not in multi

    no_sample_dir = tmp_path / "no_sample"
    write_json(no_sample_dir / "manifest.json", {"sample_paths": [], "asset_paths": [str(no_sample_dir / "a1.mp4")]})
    Phase1Analyzer().run("no_sample", no_sample_dir)
    no_sample = read_json(no_sample_dir / "analysis.json")
    assert no_sample["samples"] == []
    assert no_sample["struct_info"] == ""
    assert len(no_sample["assets"]) == 1

    invalid_sample_paths_dir = tmp_path / "invalid_sample_paths"
    write_json(
        invalid_sample_paths_dir / "manifest.json",
        {
            "sample_paths": str(invalid_sample_paths_dir / "old-single-path.mp4"),
            "asset_paths": [str(invalid_sample_paths_dir / "a1.mp4")],
        },
    )
    Phase1Analyzer().run("invalid_sample_paths", invalid_sample_paths_dir)
    invalid_sample_paths = read_json(invalid_sample_paths_dir / "analysis.json")
    assert invalid_sample_paths["samples"] == []


def test_video_ir_raises_when_llm_returns_no_parts(tmp_path, monkeypatch):
    path = tmp_path / "sample.mp4"

    monkeypatch.setattr(
        "backend.phase1.ffprobe",
        lambda value: MediaMeta(path=str(value), name=path.name, kind=MediaKind.video, duration=8.0),
    )

    class FakePro:
        def video(self, *args, **kwargs):
            return '{"parts":[]}', {}

    analyzer = Phase1Analyzer.__new__(Phase1Analyzer)
    analyzer.pro = FakePro()

    with pytest.raises(RuntimeError, match="video LLM returned no valid parts"):
        analyzer._video_ir(path)


def test_phase2_auto_selects_profile_and_compiler_gets_single_sample_detail(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path)
    settings.runs_dir.mkdir(parents=True, exist_ok=True)

    job_dir = tmp_path / "job"
    analysis = AnalysisBundle(
        job_id="job",
        target_requirement="突出收纳前后对比",
        struct_info="样例主结构",
        samples=[_analyzed_video_asset("sample_1", "sample", "sample.mp4")],
        assets=[_asset("asset_1", "asset", "asset.mp4")],
    )
    write_json(job_dir / "analysis.json", analysis)

    def fake_list_profiles(include_content=False):
        assert include_content is False
        return [{"id": "profile_a", "summary": "收纳改造结构"}]

    def fake_select_profiles(assets, target_requirement, profiles, *, raw_log_dir=None):
        assert [asset.id for asset in assets] == ["asset_1"]
        assert target_requirement == "突出收纳前后对比"
        assert profiles == [{"id": "profile_a", "summary": "收纳改造结构"}]
        assert raw_log_dir == job_dir / "llm_raw"
        return {"selected_ids": ["profile_a"], "reason": "target matches storage profile"}

    def fake_get_profiles(profile_ids):
        assert profile_ids == ["profile_a"]
        return [{"id": "profile_a", "summary": "收纳改造结构", "struct_info": "profile struct content"}]

    captured: dict[str, object] = {}

    def fake_compile(self, compiler_analysis, observations):
        captured["analysis"] = compiler_analysis
        return {
            "plan": {
                "title": "收纳对比短视频",
                "format": "vertical",
                "width": 1080,
                "height": 1920,
                "duration": 3,
                "slots": [
                    {
                        "id": "slot_1",
                        "start_time": 0,
                        "end_time": 3,
                        "source_asset_id": "asset_1",
                        "media_start": 0,
                        "role": "hook",
                        "onscreen_text": "前后对比",
                        "transition": "cut",
                    }
                ],
            },
            "raw": "{}",
            "tool_calls": [],
        }

    monkeypatch.setattr("backend.agent.list_profiles", fake_list_profiles)
    monkeypatch.setattr("backend.agent.select_profiles_for_analysis", fake_select_profiles)
    monkeypatch.setattr("backend.agent.get_profiles", fake_get_profiles)
    monkeypatch.setattr(CreativeCompilerAgent, "compile", fake_compile)
    monkeypatch.setattr(SakugaCutAgent, "_ensure_render", lambda self, plan, analysis: None)
    monkeypatch.setattr(SakugaCutAgent, "_write_video_script", lambda self, plan, analysis: None)

    plan = SakugaCutAgent("job", job_dir).run()

    assert plan.slots[0].source_asset_id == "asset_1"
    compiler_analysis = captured["analysis"]
    assert isinstance(compiler_analysis, dict)
    assert "samples" not in compiler_analysis
    assert compiler_analysis["sample_count"] == 1
    assert compiler_analysis["sample_assets"][0]["id"] == "sample_1"
    assert compiler_analysis["sample_assets"][0]["role"] == "sample"
    assert len(compiler_analysis["sample_assets"][0]["video_parts"]) == 12
    assert len(compiler_analysis["sample_assets"][0]["music_parts"]) == 9
    assert len(compiler_analysis["sample_assets"][0]["asr_parts"]) == 9
    assert compiler_analysis["target_requirement"] == "突出收纳前后对比"
    assert compiler_analysis["selected_knowledge_profiles"][0]["struct_info"] == "profile struct content"

    updated = read_json(job_dir / "analysis.json")
    assert updated["selected_knowledge_profile_ids"] == ["profile_a"]
    assert read_json(job_dir / "knowledge_selection.json")["reason"] == "target matches storage profile"


def test_compiler_analysis_uses_struct_info_only_for_multiple_samples():
    analysis = AnalysisBundle(
        job_id="job",
        target_requirement="多样例混合参考",
        struct_info="combined sample struct",
        samples=[
            _analyzed_video_asset("sample_1", "sample", "sample1.mp4"),
            _analyzed_video_asset("sample_2", "sample", "sample2.mp4"),
        ],
        assets=[_asset("asset_1", "asset", "asset.mp4")],
    )

    compiler_analysis = _analysis_for_compiler(analysis, [])

    assert "samples" not in compiler_analysis
    assert compiler_analysis["sample_count"] == 2
    assert compiler_analysis["sample_assets"] == []
    assert compiler_analysis["struct_info"] == "combined sample struct"


def test_compiler_analysis_includes_compact_revision_context():
    analysis = AnalysisBundle(
        job_id="job",
        target_requirement="保留上一版节奏",
        assets=[_asset("asset_1", "asset", "asset.mp4")],
    )
    revision_context = {
        "parent_job_id": "parent",
        "base_job_id": "parent",
        "revision_index": 2,
        "instruction": "结尾 CTA 改成关注账号",
        "previous": {
            "job_id": "parent",
            "plan": {"title": "上一版", "raw_agent": "x" * 1000, "slots": [{"id": "slot_1"}]},
            "video_script": "脚本" * 3000,
            "output": "output.mp4",
        },
        "history": [{"revision_index": idx, "instruction": f"edit {idx}"} for idx in range(12)],
    }

    compiler_analysis = _analysis_for_compiler(analysis, [], revision_context)

    compact = compiler_analysis["revision_context"]
    assert compact["instruction"] == "结尾 CTA 改成关注账号"
    assert compact["previous"]["plan"]["title"] == "上一版"
    assert "raw_agent" not in compact["previous"]["plan"]
    assert len(compact["previous"]["video_script"]) < len(revision_context["previous"]["video_script"])
    assert [row["revision_index"] for row in compact["history"]] == list(range(4, 12))


def test_generated_tts_reuse_requires_matching_text_hash():
    old_text = "上一版旁白"
    new_text = "新版旁白"
    analysis = AnalysisBundle(
        job_id="job",
        assets=[
            AssetIR(
                id="asset_tts_1",
                role="asset",
                path="tts.mp3",
                kind=MediaKind.audio,
                notes=[
                    "generated_tts=true",
                    "tts_for_slot=slot_1",
                    f"tts_text_sha1={hashlib.sha1(old_text.encode('utf-8')).hexdigest()}",
                ],
            )
        ],
    )

    assert _analysis_has_tts_for_slot(analysis, "slot_1", old_text)
    assert not _analysis_has_tts_for_slot(analysis, "slot_1", new_text)


def test_hyperframes_subagent_prompt_does_not_receive_analysis(tmp_path):
    analysis = AnalysisBundle(
        job_id="job",
        target_requirement="TARGET REQUIREMENT SHOULD NOT LEAK",
        struct_info="STRUCT INFO SHOULD NOT LEAK",
        samples=[_asset("sample_1", "sample", "sample.mp4")],
        assets=[_asset("asset_1", "asset", "asset.mp4")],
        selected_knowledge_profile_ids=["profile_should_not_leak"],
        knowledge_selection_reason="KNOWLEDGE REASON SHOULD NOT LEAK",
    )
    plan = TimelinePlan(
        title="已编译计划",
        width=1080,
        height=1920,
        duration=3,
        slots=[
            TimelineSlot(
                id="slot_1",
                start_time=0,
                end_time=3,
                source_asset_id="asset_1",
                media_start=0,
                role="hook",
                onscreen_text="按计划实现",
                transition="cut",
            )
        ],
        packaging={"subtitle_style": "bold"},
        explanation="主 Agent 已完成结构迁移。",
    )
    subagent = HyperframesSubAgent("job", tmp_path, plan, analysis)
    captured: dict[str, object] = {}

    class FakeClient:
        def text(self, prompt, **kwargs):
            captured["prompt"] = json.loads(prompt)
            return json.dumps({"html": "<html><body></body></html>"}), {}

    subagent.client = FakeClient()
    response = subagent._ask_llm(
        {"asset_1": "assets/asset_1.mp4"},
        {
            "assets": [{"id": "asset_1", "kind": "video", "hyperframes_src": "assets/asset_1.mp4"}],
            "cjk_font": {"family": "SakugaCJK", "src": "assets/font.otf"},
            "expected_visual_asset_ids": ["asset_1"],
            "expected_audio_asset_ids": [],
        },
        "assets/font.otf",
        [],
    )

    assert response is not None
    prompt = captured["prompt"]
    assert isinstance(prompt, dict)
    assert "analysis" not in prompt
    serialized = json.dumps(prompt, ensure_ascii=False)
    assert "STRUCT INFO SHOULD NOT LEAK" not in serialized
    assert "TARGET REQUIREMENT SHOULD NOT LEAK" not in serialized
    assert "profile_should_not_leak" not in serialized
    assert "KNOWLEDGE REASON SHOULD NOT LEAK" not in serialized
