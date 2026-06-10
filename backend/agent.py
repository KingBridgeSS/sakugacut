from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import uuid
import hashlib
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from urllib.request import Request, urlopen

from .ark import ArkError, extract_response_tool_calls, json_schema_format, pro_client
from .config import settings
from .json_utils import extract_json, read_json, to_plain, write_json
from .knowledge import get_profiles, list_profiles, select_profiles_for_analysis
from .media import detect_kind, ffprobe, run_cmd
from .models import AnalysisBundle, AssetIR, AudioIR, MediaKind, TimelinePlan, TimelineSlot, ToolCall, ToolResult, VideoIR
from .storage import add_artifact, add_progress, log_event
from .tts import DoubaoTTSClient


# 主创作 Agent 的系统约束：要求它把 phase1 分析结果编译为可执行时间轴 plan。
AGENT_INSTRUCTIONS = """
你的任务是把当前样例参考、用户素材、目标要求和选中的 knowledge profile 编译成一份可执行视频剪辑 plan。目标时长由你根据用户目标、用户素材可用内容、ASR 人声、真实演示音效和信息完整度自动决定。你需要尽量完整、自然地使用用户的高价值素材，可以适当舍弃重复、低信息量或不适合当前目标的部分。
时长决策优先级：
1. 用户明确指定的目标时长最高，必须优先满足。
2. 用户未指定目标时长时，不要迁移样例或 knowledge profile 的绝对秒数；只迁移叙事结构、段落功能、信息顺序、包装风格和音乐情绪。
3. 样例或 knowledge profile 中出现的 0-15s、0-1.2s、13-15s 等时间戳只是原样例观察，不是当前成片时长约束。
4. 如果用户素材包含连续讲解、产品参数介绍、功能演示、乐器/音色实测或其他需要被听清的真实原声，且用户未指定短时长，默认生成 25-45 秒的自然节奏短视频；不要为了贴合 15 秒样例而压缩高价值内容。
analysis.sample_assets 如果非空，代表当前唯一样例的详细分析，必须优先参考它的镜头、脚本、包装和声音结构，再结合用户素材做迁移；此时 analysis.struct_info 只作为辅助摘要或兜底，不作为主要依据。
如果没有 analysis.sample_assets 且 analysis.struct_info 非空，analysis.struct_info 是当前样例视频脚本、包装和背景音乐结构的主要结构参考，必须优先参考它，再结合用户素材做迁移。
如果没有样例详细分析/struct_info 且没有选中的 knowledge profile，请仅基于用户素材 assets 和目标要求生成 plan。
选中的 knowledge profile 内容是额外上下文/风格/领域知识；如果没有样例视频、sample_assets 和 struct_info 都为空，knowledge profile 可以作为主要抽象结构参考，但不得直接复制其绝对时长、时间点、镜头数量或节奏密度，除非用户明确要求“同款时长”或“同款节奏”。
样例视频只能作为结构参考，不能作为成片素材；final_plan.slots 的 source_asset_id 必须使用用户素材 asset_1、asset_2 等。若需要样例同款搜索框/CTA，请在 notes/packaging 中要求 HyperFrames 生成包装图形。
如果判断用户素材覆盖不足或缺失部分画面，可以通过三种方式补位：复用已有用户素材、对可用视频素材慢放、或用 HyperFrames 生成文字信息画面。需要文字信息补位时写入 slot.visual_fallback_text,注意不要遮挡原视频的文字信息，把生成的文字位置写到packaging里。
字幕/叠字避让规则：
- analysis.assets.video.parts 的 description 如果写到“底部字幕显示”“顶部字幕显示”“画面文字”“原素材自带字幕”等，代表源视频对应时间段已经有烧录文字；这些烧录文字是画面核心信息，不能被新生成的 onscreen_text、标题、贴纸或 CTA 覆盖。
- 选择 slot.media_start/end_time 时必须检查该源时间段是否命中已有烧录文字。命中时，优先复用原素材字幕和原声传递信息，避免再生成同义字幕；如果仍需要额外 onscreen_text，必须在 slot.notes 或 packaging 中明确写“避开原素材底部/顶部字幕区，放在上方/侧边/角标安全区”，不要只写“底部字幕”。
- 不要把“底部白字黑描边”作为默认字幕方案。只有确认源片段底部没有自带字幕、产品主体和手部操作也不会被挡住时，才允许使用底部字幕。
- 对带原声讲解且原视频已有同步字幕的片段，onscreen_text 应短而稀疏，优先做卖点角标或段落标题；避免长句、多行字幕和原素材字幕同时存在。
需要快放/慢放时写入 slot.playback_rate，1.0 为原速，小于 1 为慢放，大于 1 为快放。
快放/慢放规则：
- playback_rate > 1.0 只用于无关键人声、无关键实测音效的视觉 b-roll，或用户明确要求快节奏压缩时。
- 如果 slot 覆盖 ASR 人声、产品讲解、口播、乐器演示、真实环境声等需要被听清的内容，原则上 playback_rate 必须为 1.0；最多只能轻微加速到 1.15-1.25，并必须说明原因。
- playback_rate >= 1.5 的片段不能在 audio_strategy 中写“保留原素材解说人声/真实音效”，因为快放后原声不可自然理解。
- 不允许用 2x 以上快放来解决“素材太长但样例/profile 很短”的冲突；应改为延长成片、拆成更多 slot、或舍弃低价值片段。
慢放一般用来在用户素材缺失或强调画面的时候才用。
如果 analysis.revision_context 存在，代表用户正在修改已经生成过的视频。必须把 previous.plan 当作上一版成片的直接上下文，严格执行 revision_context.instruction；用户没有要求改变的素材映射、节奏结构、音频策略、包装和 CTA 默认保持上一版意图。仍然必须输出一份完整的新 plan，而不是差量补丁。
必须在每次回复内容中给出一份 plan；后端会清洗为 final_plan，后续所有步骤只使用 final_plan。
工具调用通过系统提供的 function calling tools 完成，不要把 tool_calls 写进回复内容。
如果判断某个 asset 视频只有音乐没有语音，且用户提供了合适的 asset 音乐，请用 ffmpeg 去除原 asset 视频的音乐，最终视频使用用户提供的音乐作为独立音轨。
最终 plan 必须显式说明 audio_strategy：逐段判断保留原片原声、压低原声叠加新音源、替换音源、静音，或插入 TTS/旁白。
TTS旁白不是必需品，你需要综合考虑要不要添加旁白。如果添加，请注意考虑时间轴上是否和原视频的语音冲突。
不要为了套用样例音乐结构而默认静音用户素材；如果用户素材本身有 speech_present、乐器演示、环境声或其他对说服力有价值的声音，优先保留对应片段原声。
只有在原声确实不可用、会干扰当前目标要求，或已有可引用的替代音频/TTS 文件时，才允许替换音源或静音。
如果需要 TTS/旁白，请在对应 slot.narration 写入要合成的口播文本，并调用 generate_tts 生成可引用音频；后端也会为未显式调用工具的 narration 自动补 TTS。
TTS 文案必须能在对应 slot 时长内自然读完；短视频中文口播按每秒约 4-5 个汉字估算，宁可少说一点，也不要让 TTS 跨入下一段。
输出 plan 前必须自检：
- duration 是否由用户目标和用户素材决定，而不是被样例/profile 秒数锚定。
- 是否存在保留原声但 playback_rate > 1.25 的 slot；如果有，必须改为原速、延长时长或改为静音/替换音频。
- 是否为了塞进短时长而把连续讲解/实测内容大倍率快放；如果有，必须延长成片或删减低价值内容。
- 是否存在“源视频已有底部/顶部烧录字幕，却又把新 onscreen_text 放在同一区域”的风险；如果有，必须改为不加新字幕、改用角标/顶部/侧边，或在 packaging 中明确避让位置。
- explanation 中必须说明当前 duration 的依据，以及为什么没有不合理压缩用户素材。
generate_tts 必须在 generate_hyperframes 之前完成；不要发明 TTS 文件名。
generate_hyperframes 只用于最终生成 HyperFrames HTML：必须在 plan 已完整、所有必要的 exec_ffmpeg/generate_tts 调用都已决定之后才请求调用；不要把它用于中间预览或草稿生成。若不确定是否需要调用，可以省略，宿主会在渲染前补跑。"""


# 单个时间轴片段的输出契约；后端会按这个 schema 清洗成 TimelineSlot。
TIMELINE_SLOT_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "description": "稳定片段 ID，例如 slot_1。"},
        "start_time": {"type": "number", "description": "片段在成片时间轴中的开始秒数。"},
        "end_time": {"type": "number", "description": "片段在成片时间轴中的结束秒数，必须大于 start_time。"},
        "source_asset_id": {"type": "string", "description": "使用的用户素材 ID，必须使用 asset_1、asset_2 等；样例视频只能参考，不能作为成片素材。"},
        "source_path": {"type": "string", "description": "可选，素材文件路径；通常只填写 source_asset_id。"},
        "media_start": {"type": "number", "description": "从源素材中开始取用的秒数。"},
        "playback_rate": {"type": "number", "description": "素材播放倍率，1.0 为原速，小于 1 为慢放，大于 1 为快放。"},
        "role": {"type": "string", "description": "片段叙事作用，如 hook、build、proof、turn、cta。"},
        "onscreen_text": {"type": "string", "description": "画面字幕或贴纸文案。"},
        "visual_fallback_text": {"type": "string", "description": "素材缺失或覆盖不足时，由 HyperFrames 生成的文字信息画面内容。"},
        "narration": {"type": "string", "description": "可选旁白或口播文本。"},
        "transition": {"type": "string", "description": "进入下一段的转场，如 cut、match_cut、whip、fade。"},
        "notes": {"type": "string", "description": "实现备注，包括构图、节奏、音频处理等。"},
    },
    "required": ["id", "start_time", "end_time", "source_asset_id", "media_start", "role", "onscreen_text", "transition"],
    "additionalProperties": False,
}


# 整个成片计划的输出契约；plan 是后续工具和渲染阶段唯一可信输入。
TIMELINE_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "成片标题。"},
        "format": {"type": "string", "enum": ["vertical", "horizontal"], "description": "成片画幅。"},
        "width": {"type": "integer", "description": "成片宽度。"},
        "height": {"type": "integer", "description": "成片高度。"},
        "duration": {"type": "number", "description": "成片总时长，单位秒。"},
        "slots": {"type": "array", "items": TIMELINE_SLOT_SCHEMA, "minItems": 1, "description": "完整时间轴片段。"},
        "gaps": {"type": "array", "items": {"type": "string"}, "description": "缺口或风险。"},
        "packaging": {
            "type": "object",
            "description": "字幕、构图、色彩、节奏等包装方向。",
            "additionalProperties": {"type": "string"},
        },
        "audio_strategy": {
            "type": "string",
            "description": "成片音频策略：逐段说明保留原声、压低原声、替换音源、静音或插入 TTS 的判断。",
        },
        "explanation": {"type": "string", "description": "说明如何迁移样例结构并映射用户素材。"},
        "missing_assets": {"type": "array", "items": {"type": "string"}, "description": "缺失素材说明。"},
    },
    "required": ["title", "format", "width", "height", "duration", "slots"],
    "additionalProperties": False,
}


AGENT_RESPONSE_FORMAT = json_schema_format(
    "sakugacut_agent_response",
    {
        "type": "object",
        "properties": {
            "plan": TIMELINE_PLAN_SCHEMA,
            "final": {"type": "boolean", "description": "是否认为 plan 已可执行。"},
            "notes": {"type": "string", "description": "给后端的简短备注。"},
        },
        "required": ["plan"],
        "additionalProperties": False,
    },
)


VIDEO_SCRIPT_INSTRUCTIONS = """你是 sakugacut 的短视频脚本交付专家。
你只根据已确定的 analysis、final_plan 和渲染信息生成视频脚本，不要修改剪辑 plan。
必须忠实描述 final_plan 和实际渲染产物的音频策略：如果 plan/HTML 保留了用户素材原声，不要写成“原素材无可用音频”或“全部去除原素材音频”。
只有当 final_plan 明确替换音源、或渲染产物确实引用了独立替代音频/TTS 文件时，才可以描述为“替换为 BGM/TTS/AI 配音”。
如果 analysis 或 final_plan 显示某段源素材已经有底部/顶部自带字幕，而 final_plan 又在同一区域安排了新字幕，脚本中必须把它标为“字幕遮挡风险/待优化点”，不要把两层字幕同时出现描述成正常或推荐的包装方案。
描述字幕位置时要区分“原素材自带烧录字幕”和“HyperFrames 新增字幕/叠字”；如果两者同时存在，明确说明新增字幕应避让原素材字幕区。
脚本必须由中文 markdown 字符串组成，并包含：
1. 成片 demo 概述：主题、时长、核心结构迁移方式。
2. 分镜/时间轴脚本：逐段说明时间、素材、画面、字幕、音乐/音效、转场。
3. 用户素材缺失判断：判断素材是否缺失或覆盖不足，标注缺失部分。
4. 补充建议：给出用户后续应该补拍、补图、补配音、补音乐或补包装素材的建议。
5. 当前成片 demo 的补充方案：说明在素材不足时，当前 demo 如何用现有素材、裁切、字幕、节奏或包装进行替代。"""


VIDEO_SCRIPT_RESPONSE_FORMAT = json_schema_format(
    "sakugacut_video_script",
    {
        "type": "object",
        "properties": {
            "video_script": {
                "type": "string",
                "description": "中文 markdown 视频脚本，包含 demo 描述、分镜、素材缺失判断、补充建议和当前 demo 补充方案。",
            },
        },
        "required": ["video_script"],
        "additionalProperties": False,
    },
)


# 主 Agent 可调用的工具白名单。真正执行逻辑都在 ToolBox 中，LLM 只提交结构化请求。
MAIN_AGENT_TOOLS = [
    {
        "type": "function",
        "name": "generate_hyperframes",
        "description": "根据后端清洗后的 final_plan 生成最终 HyperFrames standalone index.html。只在 plan 已完整、所有必要的 exec_ffmpeg/generate_tts 调用都已决定之后请求调用；不要用于中间预览或草稿生成，也不要传入另一个 plan。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "exec_ffmpeg",
        "description": "在当前 job 目录内运行 ffmpeg 或 ffprobe。用于探测媒体，或把只有音乐无语音的用户视频处理成无原声版本。",
        "parameters": {
            "type": "object",
            "properties": {
                "argv": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "推荐使用的参数数组，第一项必须是 ffmpeg 或 ffprobe；路径相对当前 job 目录。",
                },
                "command": {
                    "type": "string",
                    "description": "备用完整命令字符串，必须以 ffmpeg 或 ffprobe 开头；含空格路径时优先使用 argv。",
                },
                "timeout": {"type": "integer", "description": "超时秒数，默认 240。"},
                "purpose": {
                    "type": "string",
                    "description": "调用目的，如 strip_video_audio、probe_media、normalize_audio。",
                },
                "replace_asset_id": {
                    "type": "string",
                    "description": "如果输出文件应替换某个素材，填写对应 asset id；后端会记录该意图。",
                },
            },
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "generate_tts",
        "description": "调用豆包语音合成 API，把旁白/TTS 文本生成 mp3，并作为新的用户音频素材加入当前 job。必须在 generate_hyperframes 之前调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "需要合成的旁白/TTS 文本。"},
                "slot_id": {"type": "string", "description": "这段 TTS 对应的 plan slot id，例如 slot_2。"},
                "asset_id": {"type": "string", "description": "可选的生成音频素材 id；默认自动生成 asset_tts_N。"},
                "speaker": {"type": "string", "description": "可选豆包音色 ID；默认读取 DOUBAO_TTS_SPEAKER。"},
                "resource_id": {"type": "string", "description": "可选资源 ID；默认读取 DOUBAO_TTS_RESOURCE_ID。"},
                "speech_rate": {"type": "integer", "description": "语速，范围 -50 到 100，默认 0。"},
                "loudness_rate": {"type": "integer", "description": "音量，范围 -50 到 100，默认 0。"},
                "reason": {"type": "string", "description": "为什么需要这段 TTS。"},
            },
            "required": ["text", "reason"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


class CreativeCompilerAgent:
    def __init__(self, raw_log_dir: str | Path | None = None):
        self.client = pro_client(settings.agent_timeout, raw_log_dir=raw_log_dir)

    def compile(self, analysis: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not self.client.enabled:
            return None
        # 给主 Agent 的输入只保留编译 plan 所需的信息，并带上最近失败观察供它自我修正。
        prompt = {
            "analysis": analysis,
            "observations": observations[-6:],
            "requirement": (
                "若 analysis.sample_assets 非空，先以唯一样例的详细分析迁移脚本/包装/音乐结构，analysis.struct_info 只作辅助摘要；"
                "否则若 analysis.struct_info 非空，再以它迁移当前样例结构。"
                "选中的 knowledge profile 是额外上下文/风格/领域知识；如果没有样例视频，它可以作为主要抽象结构参考，"
                "但不得直接迁移其绝对时长、时间点、镜头数量或节奏密度，除非用户明确要求同款时长或同款节奏。"
                "用户未指定目标时长时，duration 必须由用户素材的可用内容、ASR 人声、真实演示音效和信息完整度决定；"
                "不要为了贴合样例/profile 的固定时长结构而压缩高价值素材，除非必要不要大倍率快放来贴合短时长。"
                "如果用户素材包含连续讲解、产品参数介绍、功能演示、乐器/音色实测等需要被听清的原声内容，"
                "如果 analysis.revision_context 存在，先基于 previous.plan 增量执行用户修改指令，未被要求改变的内容默认继承上一版意图。"
                "样例视频只允许参考，不能作为成片 source_asset_id；CTA/搜索框等样例包装必须让 HyperFrames 用 HTML/CSS 生成。"
                "用户素材缺失或覆盖不足时，可以复用已有用户素材、慢放可用视频素材，或在 slot.visual_fallback_text 中写入由 HyperFrames 生成的文字信息画面。"
                "快放/慢放用 slot.playback_rate 表达；覆盖 ASR 人声、产品讲解、口播、乐器演示或真实环境声的 slot 原则上 playback_rate=1.0，"
                "最多轻微加速到 1.15-1.25；playback_rate>=1.5 时不能在 audio_strategy 中声称保留原素材解说人声/真实音效。"
                "输出前自检 duration 是否被样例/profile 秒数锚定，是否存在保留原声但大倍率快放，explanation 必须说明当前 duration 的依据。"
                "只产出一份完整 plan；工具调用若有必要，使用系统提供的 function calling tools。"
            ),
        }
        instructions = _agent_instructions()
        for attempt in range(3):
            try:
                # 允许模型原生 function calling；同时用 response_format 约束它必须返回 plan。
                raw, data = self.client.text(
                    json.dumps(prompt, ensure_ascii=False),
                    instructions=instructions,
                    response_format=AGENT_RESPONSE_FORMAT,
                    tools=MAIN_AGENT_TOOLS,
                    tool_choice="auto",
                )
                break
            except ArkError as exc:
                # 只对限流类 ArkError 做退避重试，其他错误直接交给上层走兜底/失败路径。
                if not _retryable_ark_error(exc) or attempt == 2:
                    return None
                time.sleep(10 * (attempt + 1))
        else:
            return None
        parsed = extract_json(raw)
        response = parsed if isinstance(parsed, dict) else {}
        # 同时兼容原生 tool calls 和旧版把 tool_calls 塞进 JSON 的返回形式。
        native_calls = _tool_calls(extract_response_tool_calls(data))
        legacy_calls = _tool_calls(response.pop("tool_calls", None))
        response["tool_calls"] = _merge_tool_calls(native_calls, legacy_calls)
        response["raw"] = raw
        return response


class VideoScriptWriter:
    def __init__(self, raw_log_dir: str | Path | None = None):
        self.client = pro_client(settings.agent_timeout, raw_log_dir=raw_log_dir)

    def write(self, analysis: AnalysisBundle, plan: TimelinePlan, output_path: Path) -> str:
        if not self.client.enabled:
            raise RuntimeError("video script llm is unavailable")
        # 脚本生成发生在渲染之后，必须描述已生成 demo，而不是重新规划理想视频。
        prompt = {
            "task": "为这个已渲染的 SakugaCut demo 生成最终 video_script markdown。",
            "analysis": _analysis_for_script(analysis),
            "final_plan": to_plain(plan),
            "rendered_demo": {
                "path": str(output_path),
                "exists": output_path.exists(),
                "size": output_path.stat().st_size if output_path.exists() else 0,
                "has_audio": _mp4_has_audio(output_path) if output_path.exists() else False,
            },
            "requirements": [
                "脚本必须描述当前已渲染 demo，而不是理想的未来视频。",
                "如果 analysis.struct_info 非空，把它作为当前样例结构参考。",
                "如果使用了选中的 knowledge profile，把它们描述为额外上下文/风格/领域知识，而非用户素材。",
                "判断用户素材是否缺失或不足以覆盖已迁移的样例结构。",
                "对每个缺失或薄弱的素材项，给出实用的补充建议。",
                "同时说明当前 demo 对缺失部分的变通或替代方案。",
                "在 JSON 响应中只返回 video_script 字符串。",
            ],
        }
        raw, _ = self.client.text(
            json.dumps(prompt, ensure_ascii=False),
            instructions=VIDEO_SCRIPT_INSTRUCTIONS,
            response_format=VIDEO_SCRIPT_RESPONSE_FORMAT,
        )
        parsed = extract_json(raw)
        script = str((parsed or {}).get("video_script") or "").strip() if isinstance(parsed, dict) else ""
        if not script:
            raise RuntimeError("video script llm returned empty script")
        return script


class SakugaCutAgent:
    def __init__(self, job_id: str, job_dir: Path):
        self.job_id = job_id
        self.job_dir = job_dir
        self.raw_log_dir = job_dir / "llm_raw"
        self.compiler = CreativeCompilerAgent(self.raw_log_dir)
        self.script_writer = VideoScriptWriter(self.raw_log_dir)
        self.tools = ToolBox(job_id, job_dir)

    def run(self) -> TimelinePlan:
        # phase2 从 phase1 写出的 analysis.json 开始，缺少用户素材时无法生成成片。
        analysis_data = read_json(self.job_dir / "analysis.json")
        if not analysis_data:
            raise RuntimeError("analysis.json not found; run phase1 first")

        analysis = AnalysisBundle(**analysis_data)
        if not analysis.assets:
            raise RuntimeError("analysis.json must include at least one user asset for phase2")
        selected_profiles = self._resolve_knowledge_profiles(analysis)
        revision_context = read_json(self.job_dir / "revision_context.json", {}) or {}
        compiler_analysis = _analysis_for_compiler(analysis, selected_profiles, revision_context)
        observations: list[dict[str, Any]] = []
        final_plan: TimelinePlan | None = None
        final_response: dict[str, Any] = {}
        max_plan_attempts = 3

        log_event(
            self.job_id,
            "phase2.agent.start",
            "phase2 agent started",
            {
                "max_plan_attempts": max_plan_attempts,
                "hyperframes_agent_steps": settings.hyperframes_agent_steps,
                "assets": _analysis_asset_log(analysis),
                "sample_count": len(analysis.samples),
                "target_requirement": analysis.target_requirement,
                "selected_knowledge_profile_ids": analysis.selected_knowledge_profile_ids,
                "revision": _revision_context_log(revision_context),
            },
        )
        # 最多请求三次 plan；每次失败原因都会作为 observation 反馈给下一次模型调用。
        for attempt in range(max_plan_attempts):
            log_event(
                self.job_id,
                "phase2.agent.step.start",
                f"phase2: request plan {attempt + 1}/{max_plan_attempts}",
                {"attempt": attempt + 1, "observation_count": len(observations)},
                progress=True,
            )
            response = self.compiler.compile(compiler_analysis, observations)
            if not response:
                # LLM 不可用时记录观察并重试，保留完整事件日志方便排查。
                observations.append({"type": "llm_unavailable", "message": "agent returned no response"})
                log_event(
                    self.job_id,
                    "phase2.agent.llm_unavailable",
                    "phase2: llm unavailable while requesting plan",
                    {"attempt": attempt + 1},
                    progress=True,
                )
                continue

            if response.get("plan"):
                try:
                    # 后端负责把 Agent 输出清洗为强类型 TimelinePlan，并拒绝样例素材被当作成片素材。
                    final_plan = _timeline_plan_from_agent(response["plan"], analysis)
                    final_response = response
                    log_event(
                        self.job_id,
                        "phase2.agent.plan.accepted",
                        "phase2 agent returned a parseable plan; backend cleaned final_plan",
                        {"attempt": attempt + 1, "plan": _plan_log(final_plan)},
                    )
                    break
                except Exception as exc:
                    error = {"type": "plan_parse_error", "error": str(exc), "raw": response.get("plan")}
                    observations.append(error)
                    log_event(
                        self.job_id,
                        "phase2.agent.plan_parse_error",
                        "phase2 agent plan parse failed",
                        {"attempt": attempt + 1, "error": str(exc), "plan": response.get("plan")},
                    )
                    continue
            observations.append({"type": "missing_plan", "message": "agent response did not include plan", "raw": response.get("raw")})
            log_event(
                self.job_id,
                "phase2.agent.plan_missing",
                "phase2 agent response missing plan",
                {"attempt": attempt + 1, "raw_tail": _tail_text(response.get("raw"), 1200)},
                progress=True,
            )
        if final_plan is None:
            raise RuntimeError("phase2 agent did not return a valid plan after 3 attempts")

        final_plan.raw_agent = final_response.get("raw", "")
        calls = _tool_calls(final_response.get("tool_calls"))
        log_event(
            self.job_id,
            "phase2.agent.response",
            "phase2 agent response parsed",
            {
                "has_plan": True,
                "tool_calls": [{"id": call.id, "name": call.name, "arguments": call.arguments} for call in calls],
                "raw_len": len(str(final_response.get("raw") or "")),
                "raw_tail": _tail_text(final_response.get("raw"), 1200),
            },
        )
        # 渲染前工具先执行，确保 ffmpeg 预处理和 TTS 资产已经写入 analysis。
        render_calls = [call for call in calls if call.name == "generate_hyperframes"]
        pre_render_calls = [call for call in calls if call.name != "generate_hyperframes"]
        for call in pre_render_calls:
            self._run_tool_call(call, final_plan, analysis)
        self._ensure_plan_tts_assets(final_plan, analysis)
        self._prepare_speed_variants(final_plan, analysis)
        # generate_hyperframes 必须最后执行，因为它依赖最新的 plan 和素材清单。
        for call in render_calls:
            self._run_tool_call(call, final_plan, analysis)
        log_event(
            self.job_id,
            "phase2.agent.final",
            "phase2: final_plan ready",
            {"plan": _plan_log(final_plan)},
            progress=True,
        )

        write_json(self.job_dir / "plan.json", final_plan)
        add_artifact(self.job_id, "plan", "plan.json")
        log_event(self.job_id, "phase2.plan.written", "phase2 plan written", {"plan": _plan_log(final_plan)})
        self._ensure_render(final_plan, analysis)
        self._write_video_script(final_plan, analysis)
        return final_plan

    def _resolve_knowledge_profiles(self, analysis: AnalysisBundle) -> list[dict[str, Any]]:
        requested_ids = list(dict.fromkeys(str(item).strip() for item in analysis.knowledge_profile_ids if str(item).strip()))
        if requested_ids:
            # manifest 明确指定时按用户选择加载，不再自动挑选。
            profiles = get_profiles(requested_ids)
            reason = "manual knowledge profile selection"
        else:
            # 没有手动指定时，根据用户素材和目标要求自动挑选可能相关的 profile。
            available = list_profiles(include_content=False)
            selection = select_profiles_for_analysis(analysis.assets, analysis.target_requirement, available, raw_log_dir=self.raw_log_dir)
            requested_ids = [str(item) for item in selection.get("selected_ids") or []]
            profiles = get_profiles(requested_ids)
            reason = str(selection.get("reason") or "")

        selected_ids = [str(profile.get("id")) for profile in profiles if profile.get("id")]
        analysis.selected_knowledge_profile_ids = selected_ids
        analysis.knowledge_selection_reason = reason
        write_json(self.job_dir / "analysis.json", analysis)
        write_json(
            self.job_dir / "knowledge_selection.json",
            {
                "requested_knowledge_profile_ids": analysis.knowledge_profile_ids,
                "selected_knowledge_profile_ids": selected_ids,
                "reason": reason,
                "profiles": [
                    {"id": profile.get("id"), "summary": profile.get("summary")}
                    for profile in profiles
                ],
            },
        )
        add_artifact(self.job_id, "knowledge_selection", "knowledge_selection.json")
        log_event(
            self.job_id,
            "phase2.knowledge_profiles.selected",
            f"phase2 knowledge profiles selected: {len(selected_ids)}",
            {
                "requested_knowledge_profile_ids": analysis.knowledge_profile_ids,
                "selected_knowledge_profile_ids": selected_ids,
                "reason": reason,
            },
            progress=True,
        )
        return profiles

    def _run_tool_call(self, call: ToolCall, plan: TimelinePlan, analysis: AnalysisBundle) -> ToolResult:
        # 所有工具调用统一经过这里记录输入输出，便于复盘模型决策和外部命令结果。
        log_event(
            self.job_id,
            "phase2.tool.start",
            f"phase2 tool start: {call.name}",
            {"call": to_plain(call), "plan": _plan_log(plan)},
        )
        result = self.tools.run(call, plan, analysis)
        log_event(
            self.job_id,
            "phase2.tool.result",
            f"phase2 tool result: {call.name} ok={result.ok}",
            {"call": to_plain(call), "result": _tool_result_log(result)},
        )
        if call.name == "generate_tts" and not result.ok:
            # TTS 失败会导致后续 HTML 引用缺失，因此这里直接中断。
            raise RuntimeError(result.error or result.output or "generate_tts failed")
        return result

    def _ensure_plan_tts_assets(self, plan: TimelinePlan, analysis: AnalysisBundle) -> None:
        # 即使主 Agent 忘记显式调用 generate_tts，也会按 slot.narration 自动补齐音频资产。
        for slot in plan.slots:
            text = str(slot.narration or "").strip()
            if not text or _analysis_has_tts_for_slot(analysis, slot.id, text):
                continue
            result = self.tools.generate_tts(
                {
                    "text": text,
                    "slot_id": slot.id,
                    "reason": f"auto-generate TTS for slot narration: {slot.id}",
                },
                analysis,
            )
            log_event(
                self.job_id,
                "phase2.tool.auto_tts",
                f"phase2 auto TTS for {slot.id} ok={result.ok}",
                {"slot_id": slot.id, "result": _tool_result_log(result)},
                progress=True,
            )
            if not result.ok:
                raise RuntimeError(result.error or result.output or f"auto TTS failed for {slot.id}")

    def _prepare_speed_variants(self, plan: TimelinePlan, analysis: AnalysisBundle) -> None:
        # 变速在进入 HyperFrames 前烘焙成普通视频素材，避免渲染阶段音画不同步。
        assets_by_id = {asset.id: asset for asset in analysis.assets}
        existing_ids = set(assets_by_id)
        variants_dir = self.job_dir / "speed_assets"
        changed = False
        for slot in plan.slots:
            rate = _playback_rate_value(slot.playback_rate)
            slot.playback_rate = rate
            if abs(rate - 1.0) < 0.001:
                continue
            source = assets_by_id.get(str(slot.source_asset_id or ""))
            if not source or source.kind != MediaKind.video:
                slot.playback_rate = 1.0
                continue
            src = Path(source.path)
            if not src.exists():
                raise RuntimeError(f"speed source asset does not exist: {source.id}")
            slot_duration = max(0.01, slot.end_time - slot.start_time)
            source_duration = max(0.01, slot_duration * rate)
            asset_id = _unique_asset_id(f"{source.id}_{slot.id}_speed", existing_ids)
            existing_ids.add(asset_id)
            variants_dir.mkdir(parents=True, exist_ok=True)
            out_path = variants_dir / f"{_safe_filename(asset_id)}.mp4"
            argv = _speed_variant_argv(src, out_path, slot.media_start, source_duration, rate, bool(source.video and source.video.meta.has_audio))
            log_event(
                self.job_id,
                "phase2.speed_variant.start",
                f"generate speed variant for {slot.id}",
                {
                    "slot_id": slot.id,
                    "source_asset_id": source.id,
                    "output_asset_id": asset_id,
                    "playback_rate": rate,
                    "media_start": slot.media_start,
                    "source_duration": source_duration,
                    "slot_duration": slot_duration,
                    "command": argv,
                },
                progress=True,
            )
            result = run_cmd(argv, cwd=self.job_dir, timeout=settings.render_timeout)
            out = (result.get("stdout") or "") + ("\n" + result.get("stderr", "") if result.get("stderr") else "")
            if not result["ok"]:
                log_event(
                    self.job_id,
                    "phase2.speed_variant.failed",
                    f"speed variant failed for {slot.id}",
                    {"slot_id": slot.id, "returncode": result.get("returncode"), "output_tail": _tail_text(out, 2000)},
                )
                raise RuntimeError(f"speed variant failed for {slot.id}: {out[-1200:]}")
            meta = ffprobe(out_path)
            if not meta.has_video:
                raise RuntimeError(f"speed variant has no video stream for {slot.id}")
            new_asset = AssetIR(
                id=asset_id,
                role="asset",
                path=str(out_path),
                kind=MediaKind.video,
                video=VideoIR(meta=meta, parts=list(source.video.parts if source.video else [])),
                notes=[
                    "generated_speed_variant=true",
                    f"source_asset_id={source.id}",
                    f"source_slot_id={slot.id}",
                    f"playback_rate={rate}",
                ],
            )
            analysis.assets.append(new_asset)
            assets_by_id[asset_id] = new_asset
            slot.source_asset_id = asset_id
            slot.source_path = str(out_path)
            slot.media_start = 0.0
            slot.playback_rate = 1.0
            rel = _job_relative_path(self.job_dir, out_path)
            add_artifact(self.job_id, f"speed_{asset_id}", rel)
            log_event(
                self.job_id,
                "phase2.speed_variant.complete",
                f"generated speed variant for {slot.id}",
                {"slot_id": slot.id, "asset_id": asset_id, "path": rel, "meta": to_plain(meta)},
            )
            changed = True
        if changed:
            write_json(self.job_dir / "analysis.json", analysis)

    def _ensure_render(self, plan: TimelinePlan, analysis: AnalysisBundle) -> None:
        hf_dir = self.job_dir / "hyperframes"
        output = self.job_dir / "output.mp4"

        log_event(
            self.job_id,
            "phase2.render.ensure.start",
            "phase2 render ensure started",
            {"has_index": (hf_dir / "index.html").exists(), "output": str(output), "plan": _plan_log(plan)},
        )
        if not (hf_dir / "index.html").exists():
            # 如果主 Agent 没主动触发 HTML 生成，宿主仍会补跑一次 HyperFrames 子 Agent。
            log_event(self.job_id, "phase2.render.generate_missing_html", "hyperframes index.html missing; generating")
            generated = self.tools.generate_hyperframes({}, plan, analysis)
            if not generated.ok:
                log_event(
                    self.job_id,
                    "phase2.render.generate_missing_html_failed",
                    "generate_hyperframes failed while ensuring render",
                    {"result": _tool_result_log(generated)},
                )
                raise RuntimeError(generated.error or "generate_hyperframes failed")

        # 渲染前固定执行 lint 和 inspect，避免把明显无效的 HTML 送进 render。
        lint = self.tools.exec_hyperframes({"command": "npx hyperframes lint", "cwd": "hyperframes", "strict_warnings": True}, plan, analysis)
        if not lint.ok:
            log_event(self.job_id, "phase2.render.lint_failed", "hyperframes lint failed", {"result": _tool_result_log(lint)})
            raise RuntimeError(lint.error or lint.output or "hyperframes lint failed")
        add_progress(self.job_id, "phase2: lint ok")
        log_event(self.job_id, "phase2.render.lint_ok", "phase2: lint ok", {"result": _tool_result_log(lint)})

        inspect = self.tools.exec_hyperframes(
            {"command": "npx hyperframes inspect --samples 6", "cwd": "hyperframes"},
            plan,
            analysis,
        )
        if not inspect.ok:
            log_event(self.job_id, "phase2.render.inspect_failed", "hyperframes inspect failed", {"result": _tool_result_log(inspect)})
            raise RuntimeError(inspect.error or inspect.output or "hyperframes inspect failed")
        add_progress(self.job_id, "phase2: inspect ok")
        log_event(self.job_id, "phase2.render.inspect_ok", "phase2: inspect ok", {"result": _tool_result_log(inspect)})

        render = self.tools.exec_hyperframes(
            {
                "command": f"npx hyperframes render --quality draft --output {shlex.quote(str(output))}",
                "cwd": "hyperframes",
                "timeout": settings.render_timeout,
            },
            plan,
            analysis,
        )
        if render.ok and output.exists():
            # HTML 明确包含 audio 时，输出 mp4 必须真的有音频流，防止静音成片误判为成功。
            if _html_has_audio_tag(hf_dir / "index.html") and not _mp4_has_audio(output):
                log_event(
                    self.job_id,
                    "phase2.render.audio_missing",
                    "hyperframes render completed but output.mp4 has no audio stream",
                    {"output": str(output), "result": _tool_result_log(render)},
                )
                raise RuntimeError("hyperframes render completed but output.mp4 has no audio stream")
            add_artifact(self.job_id, "output", "output.mp4")
            add_progress(self.job_id, "phase2: hyperframes render complete")
            log_event(
                self.job_id,
                "phase2.render.complete",
                "phase2: hyperframes render complete",
                {"output": str(output), "size": output.stat().st_size, "result": _tool_result_log(render)},
            )
            return

        log_event(self.job_id, "phase2.render.failed", "hyperframes render failed", {"result": _tool_result_log(render)})
        raise RuntimeError(render.error or render.output or "hyperframes render failed")

    def _write_video_script(self, plan: TimelinePlan, analysis: AnalysisBundle) -> None:
        # 最终交付脚本基于实际 output.mp4 和 final_plan 生成，作为用户可读说明文档。
        output = self.job_dir / "output.mp4"
        add_progress(self.job_id, "phase2: generate video script")
        log_event(
            self.job_id,
            "phase2.video_script.start",
            "phase2 video script generation started",
            {"output": str(output), "plan": _plan_log(plan), "struct_info_len": len(analysis.struct_info or "")},
        )
        script = self.script_writer.write(analysis, plan, output)
        path = self.job_dir / "video_script.md"
        path.write_text(script + "\n", encoding="utf-8")
        add_artifact(self.job_id, "video_script", "video_script.md")
        add_progress(self.job_id, "phase2: video script ready")
        log_event(
            self.job_id,
            "phase2.video_script.written",
            "phase2 video script written",
            {"path": str(path), "length": len(script), "tail": _tail_text(script, 1200)},
        )


class ToolBox:
    def __init__(self, job_id: str, job_dir: Path):
        self.job_id = job_id
        self.job_dir = job_dir

    def run(self, call: ToolCall, plan: TimelinePlan, analysis: AnalysisBundle) -> ToolResult:
        # 工具名到实现的唯一分发点；未知工具直接拒绝，不让模型扩展执行面。
        name = call.name
        if name == "generate_hyperframes":
            return self.generate_hyperframes(call.arguments, plan, analysis)
        if name == "exec_hyperframes":
            return self.exec_hyperframes(call.arguments, plan, analysis)
        if name == "exec_ffmpeg":
            return self.exec_ffmpeg(call.arguments, analysis)
        if name == "generate_tts":
            return self.generate_tts(call.arguments, analysis)
        return ToolResult(id=call.id, name=name, ok=False, error=f"unknown tool: {name}")

    def exec_hyperframes(self, args: dict[str, Any], plan: TimelinePlan, analysis: AnalysisBundle) -> ToolResult:
        # 只允许 HyperFrames CLI 的有限子命令，命令会被重写为配置中的包名和项目路径。
        command = str(args.get("command") or "").strip()
        if isinstance(args.get("argv"), list):
            argv = [str(x) for x in args["argv"]]
        else:
            argv = shlex.split(command)
        argv, subcommand = _normalize_hyperframes_argv(argv)
        if not argv:
            log_event(self.job_id, "tool.exec_hyperframes.rejected", "invalid hyperframes command", {"command": command})
            return ToolResult(name="exec_hyperframes", ok=False, error="command must start with npx hyperframes")
        if subcommand not in {"init", "lint", "inspect", "render"}:
            log_event(
                self.job_id,
                "tool.exec_hyperframes.rejected",
                "hyperframes subcommand not allowed",
                {"command": command, "subcommand": subcommand},
            )
            return ToolResult(name="exec_hyperframes", ok=False, error=f"hyperframes subcommand not allowed: {subcommand}")
        cwd = self._safe_cwd(str(args.get("cwd") or "."))
        run_cwd, run_argv = _project_aware_hyperframes_command(cwd, argv, subcommand)
        timeout = int(args.get("timeout") or settings.render_timeout)
        log_event(
            self.job_id,
            "tool.exec_hyperframes.start",
            f"exec_hyperframes start: {subcommand}",
            {"command": run_argv, "cwd": str(run_cwd), "timeout": timeout},
        )
        result = run_cmd(run_argv, cwd=run_cwd, timeout=timeout)
        out = (result.get("stdout") or "") + ("\n" + result.get("stderr", "") if result.get("stderr") else "")
        ok = bool(result["ok"])
        strict_warnings = bool(args.get("strict_warnings"))
        # strict_warnings 用在最终门禁：除了允许的非阻塞 warning，其余 warning 都按失败处理。
        if ok and subcommand == "lint" and strict_warnings and _hyperframes_lint_has_warnings(out):
            ok = False
        tool_result = ToolResult(name="exec_hyperframes", ok=ok, output=out[-4000:], error="" if ok else out[-1200:])
        log_event(
            self.job_id,
            "tool.exec_hyperframes.result",
            f"exec_hyperframes result: {subcommand} ok={tool_result.ok}",
            {
                "command": run_argv,
                "cwd": str(run_cwd),
                "strict_warnings": strict_warnings,
                "returncode": result.get("returncode"),
                "stdout_tail": _tail_text(result.get("stdout"), 2000),
                "stderr_tail": _tail_text(result.get("stderr"), 2000),
            },
        )
        return tool_result

    def exec_ffmpeg(self, args: dict[str, Any], analysis: AnalysisBundle | None = None) -> ToolResult:
        # ffmpeg/ffprobe 只在当前 job 目录执行；输出候选也必须落在 job 目录内。
        command = str(args.get("command") or "").strip()
        if isinstance(args.get("argv"), list):
            argv = [str(x) for x in args["argv"]]
        else:
            argv = shlex.split(command)
        if not argv or argv[0] not in {"ffmpeg", "ffprobe"}:
            log_event(self.job_id, "tool.exec_ffmpeg.rejected", "invalid ffmpeg command", {"command": command})
            return ToolResult(name="exec_ffmpeg", ok=False, error="command must start with ffmpeg or ffprobe")
        timeout = int(args.get("timeout") or 240)
        output_candidate = _ffmpeg_output_candidate(args, argv, self.job_dir)
        if output_candidate:
            output_candidate.parent.mkdir(parents=True, exist_ok=True)
        log_event(
            self.job_id,
            "tool.exec_ffmpeg.start",
            f"exec_ffmpeg start: {argv[0]}",
            {"command": argv, "cwd": str(self.job_dir), "timeout": timeout},
        )
        result = run_cmd(argv, cwd=self.job_dir, timeout=timeout)
        out = (result.get("stdout") or "") + ("\n" + result.get("stderr", "") if result.get("stderr") else "")
        ok = bool(result["ok"])
        artifacts: dict[str, str] = {}
        replacement = _ffmpeg_output_candidate(args, argv, self.job_dir, must_exist=True) if ok else None
        replace_asset_id = str(args.get("replace_asset_id") or "").strip()
        if ok and replacement and replace_asset_id and analysis:
            # 如果模型声明输出要替换某个素材，同步更新 analysis，后续 plan/render 才会使用新文件。
            if _replace_analysis_asset_path(analysis, replace_asset_id, replacement):
                rel = _job_relative_path(self.job_dir, replacement)
                artifacts[f"{replace_asset_id}_replacement"] = rel
                write_json(self.job_dir / "analysis.json", analysis)
                log_event(
                    self.job_id,
                    "tool.exec_ffmpeg.asset_replaced",
                    f"exec_ffmpeg replaced asset path: {replace_asset_id}",
                    {"asset_id": replace_asset_id, "path": str(replacement), "relative_path": rel},
                )
        tool_result = ToolResult(name="exec_ffmpeg", ok=ok, output=out[-4000:], artifacts=artifacts, error="" if ok else out[-1200:])
        log_event(
            self.job_id,
            "tool.exec_ffmpeg.result",
            f"exec_ffmpeg result: {argv[0]} ok={tool_result.ok}",
            {
                "command": argv,
                "returncode": result.get("returncode"),
                "stdout_tail": _tail_text(result.get("stdout"), 2000),
                "stderr_tail": _tail_text(result.get("stderr"), 2000),
            },
        )
        return tool_result

    def generate_hyperframes(self, args: dict[str, Any], plan: TimelinePlan, analysis: AnalysisBundle) -> ToolResult:
        # HTML 生成交给专门的子 Agent，主 Agent 不直接拼接 HyperFrames 页面。
        sub = HyperframesSubAgent(self.job_id, self.job_dir, plan, analysis)
        log_event(self.job_id, "tool.generate_hyperframes.start", "generate_hyperframes start", {"plan": _plan_log(plan)})
        try:
            path = sub.run()
            result = ToolResult(name="generate_hyperframes", ok=True, output=f"wrote {path}", artifacts={"hyperframes": "hyperframes/index.html"})
            log_event(self.job_id, "tool.generate_hyperframes.result", "generate_hyperframes ok", {"result": _tool_result_log(result)})
            return result
        except Exception as exc:
            result = ToolResult(name="generate_hyperframes", ok=False, error=str(exc))
            log_event(self.job_id, "tool.generate_hyperframes.result", "generate_hyperframes failed", {"result": _tool_result_log(result)})
            return result

    def generate_tts(self, args: dict[str, Any], analysis: AnalysisBundle) -> ToolResult:
        # TTS 生成成功后会作为新的 audio AssetIR 写回 analysis，供 HyperFrames 子 Agent 引用。
        text = " ".join(str(args.get("text") or "").split())
        if not text:
            return ToolResult(name="generate_tts", ok=False, error="TTS text is empty")
        requested_asset_id = _safe_generated_asset_id(str(args.get("asset_id") or "") or _next_tts_asset_id(analysis))
        asset_id = _unique_asset_id(requested_asset_id, {asset.id for asset in analysis.assets})
        out_path = self.job_dir / "tts" / f"{asset_id}.mp3"
        log_event(
            self.job_id,
            "tool.generate_tts.start",
            "generate_tts start",
            {
                "asset_id": asset_id,
                "slot_id": str(args.get("slot_id") or ""),
                "text_len": len(text),
                "speaker": str(args.get("speaker") or settings.doubao_tts_speaker),
                "resource_id": str(args.get("resource_id") or settings.doubao_tts_resource_id),
            },
        )
        try:
            info = DoubaoTTSClient(timeout=settings.agent_timeout).synthesize(
                text,
                out_path,
                speaker=str(args.get("speaker") or "") or None,
                resource_id=str(args.get("resource_id") or "") or None,
                speech_rate=_int_range(args.get("speech_rate"), -50, 100, 0),
                loudness_rate=_int_range(args.get("loudness_rate"), -50, 100, 0),
            )
            meta = ffprobe(out_path)
            if not meta.has_audio:
                raise RuntimeError("generated TTS file has no audio stream")
            slot_id = str(args.get("slot_id") or "").strip()
            # notes 里记录 slot 和文本 hash，用于后续自动补 TTS 时去重。
            notes = [
                "generated_tts=true",
                f"tts_text_sha1={_text_sha1(text)}",
                f"tts_speaker={info.get('speaker')}",
                f"tts_resource_id={info.get('resource_id')}",
            ]
            if slot_id:
                notes.append(f"tts_for_slot={slot_id}")
            analysis.assets.append(
                AssetIR(
                    id=asset_id,
                    role="asset",
                    path=str(out_path),
                    kind=MediaKind.audio,
                    audio=AudioIR(meta=meta),
                    notes=notes,
                )
            )
            write_json(self.job_dir / "analysis.json", analysis)
            rel = _job_relative_path(self.job_dir, out_path)
            _append_generated_tts_manifest(self.job_dir, {"asset_id": asset_id, "path": rel, "slot_id": slot_id, "text": text, "reason": args.get("reason", "")})
            add_artifact(self.job_id, f"tts_{asset_id}", rel)
            result = ToolResult(
                name="generate_tts",
                ok=True,
                output=f"generated {rel}",
                artifacts={asset_id: rel},
            )
            log_event(
                self.job_id,
                "tool.generate_tts.result",
                "generate_tts ok",
                {"asset_id": asset_id, "path": rel, "bytes": info.get("bytes"), "logid": info.get("logid"), "result": _tool_result_log(result)},
            )
            return result
        except Exception as exc:
            result = ToolResult(name="generate_tts", ok=False, error=str(exc))
            log_event(self.job_id, "tool.generate_tts.result", "generate_tts failed", {"asset_id": asset_id, "error": str(exc)})
            return result

    def _safe_cwd(self, rel: str) -> Path:
        # 工具工作目录必须限制在当前 job 目录内，避免模型通过 cwd 逃逸到项目外。
        target = (self.job_dir / rel).resolve()
        root = self.job_dir.resolve()
        if root not in target.parents and target != root:
            raise ValueError("cwd escapes job directory")
        target.mkdir(parents=True, exist_ok=True)
        return target


HYPERFRAMES_SUBAGENT_INSTRUCTIONS = """你是 sakugacut 的 HyperframesSubAgent。
你只负责根据上游 plan、素材 manifest 和 hyperframes_skills 上下文编写 HyperFrames standalone index.html。
回复内容由 response_format 约束；工具调用通过系统提供的 function calling tools 完成，不要把 tool_calls 写进回复内容。
可用工具只有 exec_hyperframes。你可以请求 npx hyperframes lint/inspect/render，但 HTML 必须由你在 html 字段中亲自写出。
不要引用绝对路径，不要发明素材文件名，只能使用 asset_manifest 中的 hyperframes_src。
样例视频是结构参考，不能作为 <video>、<audio> 或 <img> 出现在成片 HTML 中。
"""


HYPERFRAMES_RESPONSE_FORMAT = json_schema_format(
    "hyperframes_subagent_response",
    {
        "type": "object",
        "properties": {
            "html": {"type": "string", "description": "完整 standalone index.html 文档。"},
            "final": {"type": "boolean", "description": "是否认为 HTML 已可检查。"},
            "notes": {"type": "string", "description": "简短实现备注或待修复问题。"},
        },
        "required": ["html"],
        "additionalProperties": False,
    },
)


HYPERFRAMES_TOOLS = [
    {
        "type": "function",
        "name": "exec_hyperframes",
        "description": "在当前 job 的 HyperFrames 工程内运行 npx hyperframes init、lint、inspect 或 render，用于校验和渲染。",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "完整命令，必须以 npx hyperframes 开头，例如 npx hyperframes lint 或 npx hyperframes inspect --samples 6。",
                },
                "argv": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "命令参数数组；第一项必须是 npx，第二项为 hyperframes 或 --yes。",
                },
                "cwd": {"type": "string", "description": "工作目录，子 agent 应固定使用 hyperframes。"},
                "strict_warnings": {"type": "boolean", "description": "lint 时是否把 warning 视为失败。"},
                "timeout": {"type": "integer", "description": "命令超时秒数。"},
            },
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


# 中文字体资产配置。字体会被复制进每个 HyperFrames 工程，避免渲染环境缺字。
CJK_FONT_FAMILY = "SakugaCJK"
CJK_FONT_FILENAME = "NotoSansCJKsc-Regular.otf"
CJK_FONT_URL = "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"


# 负责把上游 TimelinePlan、素材清单和 HyperFrames 规范编译成可校验的 standalone index.html。
class HyperframesSubAgent:
    def __init__(self, job_id: str, job_dir: Path, plan: TimelinePlan, analysis: AnalysisBundle):
        self.job_id = job_id
        self.job_dir = job_dir
        self.plan = plan
        self.analysis = analysis
        self.hf_dir = job_dir / "hyperframes"
        self.client = pro_client(settings.agent_timeout, raw_log_dir=job_dir / "llm_raw")

    def run(self) -> Path:
        log_event(
            self.job_id,
            "hyperframes.subagent.start",
            "hyperframes subagent: scaffold",
            {"max_steps": settings.hyperframes_agent_steps, "plan": _plan_log(self.plan)},
            progress=True,
        )
        # 先准备 HyperFrames 工程、复制素材和 CJK 字体，再把可用资源写成 manifest 交给子 Agent。
        self._init_project()
        media = self._copy_media()
        cjk_font_src = self._ensure_cjk_font_asset()
        manifest = self._asset_manifest(media, cjk_font_src)
        write_json(self.hf_dir / "asset_manifest.json", manifest)
        write_json(self.hf_dir / "sakugacut_plan.json", self.plan)
        log_event(
            self.job_id,
            "hyperframes.subagent.assets_ready",
            "hyperframes media manifest ready",
            {
                "media": media,
                "cjk_font_src": cjk_font_src,
                "expected_visual_asset_ids": manifest.get("expected_visual_asset_ids"),
                "expected_audio_asset_ids": manifest.get("expected_audio_asset_ids"),
            },
        )

        # 这里不做静态 HTML 兜底：没有子 Agent 时直接失败，避免生成与创作计划不一致的假结果。
        if not self.client.enabled:
            log_event(self.job_id, "hyperframes.subagent.llm_unavailable", "hyperframes subagent llm is unavailable")
            raise RuntimeError("hyperframes subagent llm is unavailable")

        # observations 会把解析错误、材料校验和工具结果反馈给下一轮 LLM，用于迭代修正 HTML。
        observations: list[dict[str, Any]] = []
        html_written = False
        last_validation: dict[str, Any] = {"ok": False, "errors": ["no html generated"]}
        last_check: dict[str, Any] | None = None

        # 多轮循环：每轮允许子 Agent 重写 HTML，并按最新反馈决定是否继续修复。
        for step in range(settings.hyperframes_agent_steps):
            log_event(
                self.job_id,
                "hyperframes.subagent.step.start",
                f"hyperframes subagent: llm step {step + 1}/{settings.hyperframes_agent_steps}",
                {
                    "step": step + 1,
                    "observation_count": len(observations),
                    "html_written": html_written,
                    "last_validation": last_validation,
                    "last_check": last_check,
                },
                progress=True,
            )
            response = self._ask_llm(media, manifest, cjk_font_src, observations)
            if response is None:
                # LLM 返回不可解析内容时记录为 observation，便于日志定位最后一次失败原因。
                observation = {"type": "llm_error", "error": "subagent returned no parseable response"}
                observations.append(observation)
                log_event(
                    self.job_id,
                    "hyperframes.subagent.llm_no_parse",
                    "subagent returned no parseable response",
                    {"step": step + 1},
                )
                break

            parsed = response.get("parsed")
            raw = str(response.get("raw") or "")
            html_text = _extract_response_html(parsed, raw)
            calls = _tool_calls(response.get("tool_calls"))
            log_event(
                self.job_id,
                "hyperframes.subagent.response",
                "hyperframes subagent response parsed",
                {
                    "step": step + 1,
                    "parsed_keys": sorted(parsed.keys()) if isinstance(parsed, dict) else [],
                    "raw_len": len(raw),
                    "raw_tail": _tail_text(raw, 1200),
                    "html_len": len(html_text),
                    "tool_calls": [{"id": call.id, "name": call.name, "arguments": call.arguments} for call in calls],
                },
            )
            if html_text:
                # 只要本轮给出 HTML，就落盘并立即做本地材料校验，先拦住素材路径和字体问题。
                self._write_html(html_text)
                self._ensure_cjk_font_css(cjk_font_src)
                html_written = True
                last_validation = self._validate_html(media)
                observations.append(last_validation)
                log_event(
                    self.job_id,
                    "hyperframes.subagent.material_validation",
                    f"hyperframes material validation ok={last_validation.get('ok')}",
                    {"step": step + 1, "validation": last_validation},
                )

            # 子 Agent 只能调用 exec_hyperframes，用于 lint/inspect/render 等 HyperFrames CLI 校验。
            tool_results: list[ToolResult] = []
            for call in calls:
                result = self._run_subagent_tool(call)
                tool_results.append(result)
                observations.append(to_plain(result))
                log_event(
                    self.job_id,
                    "hyperframes.subagent.tool.result",
                    f"hyperframes subagent tool result: {call.name} ok={result.ok}",
                    {"step": step + 1, "call": to_plain(call), "result": _tool_result_log(result)},
                )

            # 必须先拿到 HTML、通过材料校验，并且本轮工具调用全部成功，才进入自动最终检查。
            if not html_written:
                continue
            if not last_validation.get("ok"):
                continue
            if tool_results and not all(result.ok for result in tool_results):
                continue

            # 自动跑严格 lint 和 inspect，保证即使 LLM 没主动请求工具，也有统一的最终门禁。
            check = self._auto_hyperframes_check()
            last_check = check
            observations.append(check)
            log_event(
                self.job_id,
                "hyperframes.subagent.auto_check",
                f"hyperframes auto check ok={check.get('ok')}",
                {"step": step + 1, "check": check},
            )
            if check.get("ok"):
                add_artifact(self.job_id, "hyperframes", "hyperframes/index.html")
                log_event(self.job_id, "hyperframes.subagent.complete", "hyperframes subagent produced checked html", {"path": str(self.hf_dir / "index.html")})
                return self.hf_dir / "index.html"

        # 走到这里说明步数耗尽或最后结果仍不满足门禁，按失败类型抛出更具体的错误。
        if not html_written:
            log_event(self.job_id, "hyperframes.subagent.failed", "hyperframes subagent did not write index.html")
            raise RuntimeError("hyperframes subagent did not write index.html")
        if not last_validation.get("ok"):
            error = "hyperframes subagent html failed material/font validation: " + json.dumps(last_validation, ensure_ascii=False)
            log_event(self.job_id, "hyperframes.subagent.failed", error, {"last_validation": last_validation})
            raise RuntimeError(error)
        if last_check and not last_check.get("ok"):
            error = "hyperframes subagent html failed lint/inspect: " + json.dumps(last_check, ensure_ascii=False)[:1200]
            log_event(self.job_id, "hyperframes.subagent.failed", error, {"last_check": last_check})
            raise RuntimeError(error)
        error = "hyperframes subagent exhausted steps before producing checked html"
        log_event(
            self.job_id,
            "hyperframes.subagent.failed",
            error,
            {
                "max_steps": settings.hyperframes_agent_steps,
                "last_validation": last_validation,
                "last_check": last_check,
                "html_written": html_written,
            },
        )
        raise RuntimeError(error)

    def _init_project(self) -> None:
        # 已初始化过的工程直接复用，保留可能已经安装好的 HyperFrames 依赖和配置。
        if (self.hf_dir / "hyperframes.json").exists():
            log_event(self.job_id, "hyperframes.init.reuse", "reuse existing hyperframes project", {"path": str(self.hf_dir)})
            return
        # 目录存在但不是完整工程时先清理，避免旧文件影响本次生成。
        if self.hf_dir.exists():
            shutil.rmtree(self.hf_dir)
            log_event(self.job_id, "hyperframes.init.clean", "removed stale hyperframes directory", {"path": str(self.hf_dir)})
        log_event(
            self.job_id,
            "hyperframes.init.start",
            "hyperframes init start",
            {"command": _hyperframes_argv("init", "hyperframes", "--non-interactive", "--example", "blank"), "cwd": str(self.job_dir)},
        )
        result = run_cmd(
            _hyperframes_argv("init", "hyperframes", "--non-interactive", "--example", "blank"),
            cwd=self.job_dir,
            timeout=180,
        )
        log_event(
            self.job_id,
            "hyperframes.init.result",
            f"hyperframes init ok={result['ok']}",
            {
                "returncode": result.get("returncode"),
                "stdout_tail": _tail_text(result.get("stdout"), 2000),
                "stderr_tail": _tail_text(result.get("stderr"), 2000),
            },
        )
        if not result["ok"]:
            raise RuntimeError(result["stderr"] or "hyperframes init failed")

    def _copy_media(self) -> dict[str, str]:
        # 只复制 HyperFrames 可直接引用的媒体类型，并用 asset_id 映射到相对 assets/ 路径。
        assets_dir = self.hf_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        media: dict[str, str] = {}
        for asset in self.analysis.assets:
            src = Path(asset.path)
            if src.exists() and detect_kind(src) in {MediaKind.video, MediaKind.image, MediaKind.audio}:
                copied = self._copy_asset_safe(src, assets_dir, asset.id)
                media[asset.id] = f"assets/{copied.name}"
                log_event(
                    self.job_id,
                    "hyperframes.asset.copied",
                    "copied media asset for hyperframes",
                    {"asset_id": asset.id, "source": str(src), "target": str(copied), "size": copied.stat().st_size},
                )
        return media

    def _copy_asset_safe(self, src: Path, assets_dir: Path, asset_id: str) -> Path:
        # 输出文件名来自 asset_id 的安全化版本，避免原始文件名包含空格、中文或特殊符号。
        suffix = src.suffix.lower() or ".bin"
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", asset_id).strip("_") or "asset"
        dst = assets_dir / f"{stem}{suffix}"
        shutil.copy2(src, dst)
        return dst

    def _ensure_cjk_font_asset(self) -> str:
        # 中文字体作为项目内资产引用，确保离线渲染和截图检查时中文不会退化成方框。
        assets_dir = self.hf_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        dst = assets_dir / CJK_FONT_FILENAME
        if dst.exists() and dst.stat().st_size > 1_000_000:
            log_event(self.job_id, "hyperframes.font.reuse", "reuse existing CJK font asset", {"path": str(dst), "size": dst.stat().st_size})
            return f"assets/{dst.name}"

        # 字体先落到仓库级缓存，再复制到每个 job，避免每次生成都重复下载。
        cache = settings.root / ".cache" / "fonts" / CJK_FONT_FILENAME
        if not cache.exists() or cache.stat().st_size <= 1_000_000:
            cache.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache.with_suffix(cache.suffix + ".tmp")
            req = Request(CJK_FONT_URL, headers={"User-Agent": "sakugacut/0.1"})
            log_event(self.job_id, "hyperframes.font.download.start", "download CJK font", {"url": CJK_FONT_URL, "cache": str(cache)})
            try:
                with urlopen(req, timeout=180) as response, tmp.open("wb") as fh:
                    shutil.copyfileobj(response, fh)
            except Exception as exc:
                if tmp.exists():
                    tmp.unlink()
                log_event(self.job_id, "hyperframes.font.download.failed", "failed to download CJK font", {"error": str(exc)})
                raise RuntimeError(f"failed to download CJK font for HyperFrames: {exc}") from exc
            if tmp.stat().st_size <= 1_000_000:
                tmp.unlink(missing_ok=True)
                log_event(self.job_id, "hyperframes.font.download.invalid", "downloaded CJK font is unexpectedly small")
                raise RuntimeError("downloaded CJK font is unexpectedly small")
            tmp.replace(cache)
            log_event(self.job_id, "hyperframes.font.download.complete", "downloaded CJK font", {"cache": str(cache), "size": cache.stat().st_size})

        shutil.copy2(cache, dst)
        log_event(self.job_id, "hyperframes.font.copied", "copied CJK font for hyperframes", {"source": str(cache), "target": str(dst), "size": dst.stat().st_size})
        return f"assets/{dst.name}"

    def _ensure_cjk_font_css(self, cjk_font_src: str) -> None:
        # HTML 由 LLM 生成后，再由宿主注入强制字体声明，减少 prompt 遗漏造成的中文渲染问题。
        index = self.hf_dir / "index.html"
        text = index.read_text(encoding="utf-8")
        style = f"""
    <style data-sakugacut-cjk-font>
      @font-face {{
        font-family: '{CJK_FONT_FAMILY}';
        src: url('{cjk_font_src}') format('opentype');
        font-weight: 100 900;
        font-style: normal;
        font-display: block;
      }}
      html, body, body * {{
        font-family: '{CJK_FONT_FAMILY}';
      }}
    </style>
"""
        if "data-sakugacut-cjk-font" in text:
            text = re.sub(
                r"\s*<style\s+data-sakugacut-cjk-font>[\s\S]*?</style>",
                "\n" + style.rstrip(),
                text,
                count=1,
                flags=re.IGNORECASE,
            )
        elif re.search(r"</head>", text, re.IGNORECASE):
            text = re.sub(r"</head>", style + "  </head>", text, count=1, flags=re.IGNORECASE)
        else:
            text = style + text
        index.write_text(text, encoding="utf-8")

    def _asset_manifest(self, media: dict[str, str], cjk_font_src: str) -> dict[str, Any]:
        # manifest 同时给 LLM 和本地校验使用：既告诉它能引用什么，也记录哪些素材必须出现。
        return {
            "assets": [self._asset_entry(asset, media.get(asset.id)) for asset in self.analysis.assets],
            "cjk_font": {"family": CJK_FONT_FAMILY, "src": cjk_font_src},
            "expected_visual_asset_ids": sorted(self._expected_visual_asset_ids(media)),
            "expected_audio_asset_ids": sorted(self._expected_audio_asset_ids(media)),
        }

    def _asset_entry(self, asset: Any, src: str | None) -> dict[str, Any]:
        # 将完整分析压缩成子 Agent 需要的素材摘要，避免 prompt 过大。
        meta = None
        parts: list[dict[str, Any]] = []
        if asset.video:
            meta = asset.video.meta
            parts = [
                {
                    "start_time": part.start_time,
                    "end_time": part.end_time,
                    "description": part.description,
                }
                for part in asset.video.parts[:8]
            ]
        elif asset.audio:
            meta = asset.audio.meta
        elif asset.image:
            meta = asset.image.meta

        entry: dict[str, Any] = {
            "id": asset.id,
            "role": asset.role,
            "kind": asset.kind.value if isinstance(asset.kind, MediaKind) else str(asset.kind),
            "hyperframes_src": src,
            "original_name": Path(asset.path).name,
            "duration": getattr(meta, "duration", None) if meta else None,
            "width": getattr(meta, "width", None) if meta else None,
            "height": getattr(meta, "height", None) if meta else None,
            "has_audio": getattr(meta, "has_audio", False) if meta else False,
            "has_video": getattr(meta, "has_video", False) if meta else False,
            "parts": parts,
            "notes": list(getattr(asset, "notes", []) or []),
        }
        if asset.image:
            entry["description"] = asset.image.description
            entry["visual_style"] = asset.image.visual_style
        if asset.audio and asset.audio.music:
            entry["music"] = {
                "parts": [to_plain(part) for part in asset.audio.music.parts[:6]],
            }
        if asset.audio and asset.audio.asr:
            entry["asr"] = {
                "parts": [to_plain(part) for part in asset.audio.asr.parts[:6]],
            }
        return entry

    def _ask_llm(
        self,
        media: dict[str, str],
        manifest: dict[str, Any],
        cjk_font_src: str,
        observations: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        # Prompt 明确列出 final_plan、素材白名单、HTML 结构约束和最近校验反馈。
        # 样例 struct_info 与 knowledge profile 已在主 Agent 阶段编译进 plan，不再交给子 Agent 二次解释。
        prompt = {
            "task": "为这个视频编写 runs/<job>/hyperframes/index.html。只返回 JSON。",
            "job_id": self.job_id,
            "composition": {"width": self.plan.width, "height": self.plan.height, "duration": self.plan.duration},
            "plan": to_plain(self.plan),
            "asset_manifest": manifest,
            "allowed_media_src_map": media,
            "recent_observations": observations[-8:],
            "requirements": [
                "在 html 字段中亲自编写完整的 standalone HyperFrames index.html。",
                "上游主 Agent 已经把样例 struct_info、knowledge profile 和用户目标编译进 plan；你只按 plan 实现，不重新做创作规划。",
                "样例视频只在上游用于生成 plan，不在 asset_manifest 中。不要在最终 HTML 中渲染或编造样例素材。",
                "如果 plan 要求样例风格的 CTA/搜索框，用 HTML/CSS 文本和形状生成，使用目标要求或 plan 文案。",
                "只用 asset_manifest 中的 hyperframes_src 值作为 media src。不要使用绝对路径。",
                "plan 引用的用户视觉素材必须以 <video> 或 <img> clip 出现。",
                "如果 slot.visual_fallback_text 非空，必须用 HTML/CSS 在对应 slot 内生成文字信息画面或文字叠加层，用来补足素材缺口；不要为这类文字信息发明图片素材。",
                "生成 onscreen_text 或其他文字叠加层前，必须查看对应 asset_manifest.parts/asr/music 和 plan slot 的 media_start、data-start、data-duration。parts.description 如果写到“底部字幕显示”“顶部字幕显示”“原素材自带字幕”“画面文字”等，说明视频像素里已有烧录文字；新文字必须避开这些区域。",
                "当源片段已有底部烧录字幕时，不要使用 bottom/底部字幕样式，不要把新字幕放在下 25% 画面内；优先使用顶部安全区、左上/右上角标、侧边短标签，或省略同义 onscreen_text。",
                "当源片段已有顶部烧录字幕时，不要使用 top/顶部标题样式；改用底部安全区、侧边短标签或省略同义 onscreen_text。",
                "如果 plan.packaging 写了“底部字幕”但 asset_manifest 显示同一源时间段已有底部字幕，以避让已有字幕为准；不要机械执行底部位置。把 notes 写明已避让原素材字幕区。",
                "长 onscreen_text 不得在有原素材字幕的片段中生成多行大字。此类片段的新文字应压缩为 1 行短角标，或拆成不遮挡原字幕的上方小标题。",
                "slot.playback_rate 在进入本阶段前已经由后端烘焙进派生素材；在 HTML 中不要使用 data-playback-rate、defaultPlaybackRate 或手写 media seek 逻辑。",
                "video 必须 muted playsinline；任何可听声音必须由单独的 <audio> clip 承载。",
                "对每个来源为用户 video asset 且 has_audio=true、原声可用的 plan slot，添加匹配的 <audio class=\"clip\">，使用相同的 hyperframes_src、data-start、data-duration、data-media-start，并设置明确的 data-volume。",
                "用 asset 的 notes/asr/music 字段判断音频意图：speech_present、产品演示声音、乐器演奏、有重要说话内容或有用的环境声等通常应保留；non_speech_audio 表示有音乐声音/节奏但未识别人声，只有在存在更好的用户提供音频 asset 时才可替换。",
                "不要创建 src、data-start、data-duration 和 data-media-start 完全相同的重复 <audio> clip。如果同一原始段落需要同时处理环境声和人声，使用一个 <audio> clip 并设置压低后的音量，而不是分成 bg/vo 两个重复 clip。",
                "生成的 TTS asset 带有 notes generated_tts=true，通常还有 tts_for_slot=<slot_id>；把每个放在对应 slot 的起始位置作为 <audio class=\"clip\">，当两者都应可听时压低原音频。",
                "生成的 TTS audio clip 必须在其 slot 内：设置 data-duration 不超过 slot 的 end-start 时长，即使 mp3 asset 更长。绝不让 TTS clip 在同一 data-track-index 上与下一个 slot 重叠。",
                "音频轨道必须遵守 HyperFrames 时序规则：同一 data-track-index 上的 clip 不得重叠。把同时播放的原音频和 TTS 放在不同轨道上；保持顺序 TTS clip 不重叠，或有意分配不同的轨道。",
                "如果有意将某 slot 静音而其音频可用，在 notes 中写明原因，并确保当最终视频不应无声时存在另一个 <audio> source。",
                "如果 plan 要求旁白/TTS 但 asset_manifest 中不存在生成的 TTS audio asset，渲染可视化字幕并保留/压低原音频，而不是编造 TTS 文件名。",
                "如果存在用户 audio asset，且它属于选定的音频策略，就把它作为 <audio> clip 包含进来。",
                f"中文字体必须通过 @font-face 使用 family {CJK_FONT_FAMILY} 渲染，来源为 {cjk_font_src}。",
                f"对所有可见中文文本使用 font-family: '{CJK_FONT_FAMILY}'。不要添加未打包的字体回退族。",
                "尽可能用 data-media-start 尊重 plan 的 asset_range 值。",
                "根 standalone composition 元素必须包含 data-composition-id、data-start=\"0\"、data-duration、data-width 和 data-height。",
                "给根 composition 元素一个 id，并用该 id 选择器限定 CSS 作用域，而不是 [data-composition-id=\"...\"] 选择器。",
                "多场景 clip 需要有效的 data-start、data-duration 和 data-track-index attribute。",
                "每个有时间的非根元素，包括文字叠加层，必须包含 class=\"clip\"，使运行时可见性遵循 data-start/data-duration。",
                "在 window.__timelines 中为根 data-composition-id 注册一个 paused GSAP timeline。",
                "每个在 clip 边界把元素淡出到 opacity 0 的 GSAP exit tween 后，必须紧跟 tl.set(selector, { opacity: 0 }, boundaryTime) 硬杀。",
                "把 render、media、timing 和 deterministic-seek 的 lint 警告视为需要修复的问题，在完成前处理。",
                "通过将重复的时间文字/叠加 clip 分布到几个不重叠的 data-track-index 值上，或在合适时将场景叠加分组到 wrapper clip 中，避免 timeline_track_too_dense。",
                "在编写 html 后可以调用 exec_hyperframes 进行 lint 或 inspect。",
            ],
            "hyperframes_skills": _hyperframes_skill_context(),
        }
        last_error: ArkError | None = None
        for attempt in range(3):
            try:
                raw, data = self.client.text(
                    json.dumps(prompt, ensure_ascii=False),
                    instructions=_hyperframes_instructions(),
                    response_format=HYPERFRAMES_RESPONSE_FORMAT,
                    tools=HYPERFRAMES_TOOLS,
                    tool_choice="auto",
                )
                break
            except ArkError as exc:
                last_error = exc
                if not _retryable_ark_error(exc) or attempt == 2:
                    log_event(
                        self.job_id,
                        "hyperframes.subagent.llm_error",
                        f"hyperframes subagent: llm error {str(exc)[:120]}",
                        {"error": str(exc), "attempt": attempt + 1},
                        progress=True,
                    )
                    return None
                delay = 10 * (attempt + 1)
                log_event(
                    self.job_id,
                    "hyperframes.subagent.llm_retry",
                    f"hyperframes subagent: llm rate limited, retrying in {delay}s",
                    {"error": str(exc), "attempt": attempt + 1, "delay": delay},
                    progress=True,
                )
                time.sleep(delay)
        else:
            if last_error:
                return None

        parsed = extract_json(raw)
        native_calls = _tool_calls(extract_response_tool_calls(data))
        if isinstance(parsed, dict):
            legacy_calls = _tool_calls(parsed.pop("tool_calls", None))
            return {"parsed": parsed, "raw": raw, "tool_calls": _merge_tool_calls(native_calls, legacy_calls)}
        html_text = _extract_response_html(None, raw)
        if html_text:
            return {"parsed": {"html": html_text}, "raw": raw, "tool_calls": native_calls}
        return None

    def _run_subagent_tool(self, call: ToolCall) -> ToolResult:
        # 子 Agent 的工具权限被收窄到 HyperFrames CLI，防止它执行任意 shell 或改动外部文件。
        if call.name != "exec_hyperframes":
            return ToolResult(id=call.id, name=call.name, ok=False, error="hyperframes subagent may only call exec_hyperframes")
        args = dict(call.arguments)
        args.setdefault("cwd", "hyperframes")
        result = ToolBox(self.job_id, self.job_dir).exec_hyperframes(args, self.plan, self.analysis)
        result.id = call.id
        return result

    def _auto_hyperframes_check(self) -> dict[str, Any]:
        # 最终门禁固定执行 strict lint 和 inspect，lint 警告也会被视为需要修复的问题。
        lint = self._run_subagent_tool(
            ToolCall(name="exec_hyperframes", arguments={"command": "npx hyperframes lint", "cwd": "hyperframes", "strict_warnings": True})
        )
        if not lint.ok:
            return {"type": "hyperframes_auto_check", "ok": False, "lint": to_plain(lint)}
        inspect = self._run_subagent_tool(
            ToolCall(name="exec_hyperframes", arguments={"command": "npx hyperframes inspect --samples 6", "cwd": "hyperframes"})
        )
        return {"type": "hyperframes_auto_check", "ok": bool(inspect.ok), "lint": to_plain(lint), "inspect": to_plain(inspect)}

    def _write_html(self, html_text: str) -> None:
        # 只接受完整 HTML 文档，避免把片段写成 index.html 后让后续 CLI 报难定位的错误。
        html_text = html_text.strip()
        if not re.search(r"<html\b", html_text, re.IGNORECASE):
            raise RuntimeError("hyperframes subagent html is missing <html>")
        (self.hf_dir / "index.html").write_text(html_text, encoding="utf-8")

    def _validate_html(self, media: dict[str, str]) -> dict[str, Any]:
        # 本地材料校验先检查结构、字体和素材引用，补足 HyperFrames lint 不一定覆盖的业务约束。
        index = self.hf_dir / "index.html"
        text = index.read_text(encoding="utf-8") if index.exists() else ""
        entries = _media_src_entries(text)
        srcs = {_src_path_part(entry["src"]) for entry in entries}
        errors: list[str] = []
        warnings: list[str] = []

        # 根节点必须是 standalone composition，并带齐 HyperFrames 运行所需的数据属性。
        if not re.search(r"data-composition-id\s*=", text, re.IGNORECASE):
            errors.append("index.html must contain a root data-composition-id")
        root_attrs = _root_composition_attrs(text)
        if root_attrs:
            for attr in ("data-start", "data-duration", "data-width", "data-height"):
                if not re.search(rf"\b{re.escape(attr)}\s*=", root_attrs, re.IGNORECASE):
                    errors.append(f"root composition must include {attr}")
        else:
            errors.append("index.html must contain a standalone root composition element")
        if re.search(r"<template\b", text, re.IGNORECASE):
            errors.append("standalone index.html must not wrap the root composition in <template>")
        if CJK_FONT_FAMILY not in text or "data-sakugacut-cjk-font" not in text:
            errors.append(f"index.html must include injected {CJK_FONT_FAMILY} @font-face for Chinese text")
        if not (self.hf_dir / "assets" / CJK_FONT_FILENAME).exists():
            errors.append(f"missing copied CJK font asset: assets/{CJK_FONT_FILENAME}")

        # 所有带时间属性的非根元素都必须用 clip 类，让运行时能按时间轴控制显隐。
        for entry in _timed_non_root_entries(text):
            attrs = entry["attrs"]
            if not re.search(r"\bclass\s*=\s*(['\"])[^'\"]*\bclip\b[^'\"]*\1", attrs, re.IGNORECASE):
                errors.append(f"timed non-root element must include class=\"clip\": <{entry['tag']} id=\"{entry.get('id') or ''}\">")

        # 媒体引用只能指向复制后的相对 assets/ 路径，并对视频强制静音和 playsinline。
        for entry in entries:
            src = str(entry["src"])
            src_path = _src_path_part(src)
            attrs = str(entry["attrs"]).lower()
            if "#" in src or "#" in unquote(src):
                errors.append(f"media src must not contain # fragment: {src}")
            if src_path.startswith("/") or "://" in src_path:
                errors.append(f"media src must be a relative assets/ path: {src}")
            if not src_path.startswith("assets/"):
                errors.append(f"media src must use copied hyperframes assets path: {src}")
            media_path = (self.hf_dir / src_path).resolve()
            if self.hf_dir.resolve() not in media_path.parents or not media_path.exists():
                errors.append(f"media src does not resolve to an existing copied asset: {src}")
            if not re.search(r"\bid\s*=", str(entry["attrs"]), re.IGNORECASE):
                errors.append(f"{entry['tag']} media element must include a unique id: {src}")
            if entry["tag"] == "video":
                if "muted" not in attrs:
                    errors.append(f"video must be muted; audio belongs in separate <audio>: {src}")
                if "playsinline" not in attrs:
                    errors.append(f"video must include playsinline: {src}")

        # 计划中点名的视觉素材必须真的出现在 HTML 中；否则说明生成结果没有执行上游映射。
        expected_visual = self._expected_visual_asset_ids(media)
        user_visual = {asset.id for asset in self.analysis.assets if asset.kind in {MediaKind.video, MediaKind.image} and media.get(asset.id)}
        if expected_visual:
            for asset_id in sorted(expected_visual):
                if media.get(asset_id) not in srcs:
                    errors.append(f"planned visual asset is not referenced in html: {asset_id} -> {media.get(asset_id)}")
        elif user_visual and not any(media.get(asset_id) in srcs for asset_id in user_visual):
            errors.append("html must reference at least one user visual asset")

        # 用户提供或计划使用的音频源必须作为独立 audio 标签出现，避免混在 video 声道里不可控。
        audio_srcs = {_src_path_part(entry["src"]) for entry in entries if entry["tag"] == "audio"}
        for asset_id in sorted(self._expected_audio_asset_ids(media)):
            if media.get(asset_id) not in audio_srcs:
                errors.append(f"planned/user audio source must be referenced by an <audio> tag: {asset_id} -> {media.get(asset_id)}")

        if not entries:
            warnings.append("no <video>, <audio>, or <img> tags were found")

        return {
            "type": "material_validation",
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "media_srcs": sorted(srcs),
        }

    def _expected_visual_asset_ids(self, media: dict[str, str]) -> set[str]:
        # 从计划槽位里抽取已知视觉素材 id，形成“必须被 HTML 引用”的检查集合。
        ids: set[str] = set()
        known_visual = {asset.id for asset in self.analysis.assets if asset.kind in {MediaKind.video, MediaKind.image}}
        for slot in self.plan.slots:
            slot_data = to_plain(slot)
            for value in (slot_data.get("source_asset_id"), slot_data.get("asset")):
                ids.update(_collect_known_asset_ids(value, known_visual))
        return {asset_id for asset_id in ids if media.get(asset_id)}

    def _expected_audio_asset_ids(self, media: dict[str, str]) -> set[str]:
        # 独立音频素材，以及计划中使用到且本身有音轨的视频素材，都要求 HTML 用 audio 标签显式引用。
        planned_video_ids = self._expected_visual_asset_ids(media)
        ids: set[str] = set()
        for asset in self.analysis.assets:
            if not media.get(asset.id):
                continue
            if asset.kind == MediaKind.audio:
                ids.add(asset.id)
            elif asset.kind == MediaKind.video and asset.id in planned_video_ids and asset.video and asset.video.meta.has_audio:
                ids.add(asset.id)
        return ids


def _hyperframes_skill_context() -> dict[str, str]:
    # 只抽取 HyperFrames 规范中对子 Agent 写 HTML 最关键的章节，控制 prompt 长度。
    base = settings.root / "hyperframes_skills"
    return {
        "hyperframes": _skill_sections(
            base / "hyperframes" / "SKILL.md",
            [
                "Layout Before Animation",
                "Data Attributes",
                "Composition Structure",
                "Video and Audio",
                "Timeline Contract",
                "Rules (Non-Negotiable)",
                "Scene Transitions (Non-Negotiable)",
            ],
        ),
        "hyperframes_cli": _skill_sections(
            base / "hyperframes-cli" / "SKILL.md",
            ["Workflow", "Linting", "Visual Inspect", "Rendering"],
        ),
    }


def _skill_sections(path: Path, headings: list[str]) -> str:
    # 从技能文档中截取指定二级标题；找不到标题时退回到裁剪后的全文。
    if not path.exists():
        return f"{path} not found"
    text = path.read_text(encoding="utf-8")
    parts: list[str] = []
    for heading in headings:
        match = re.search(rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
        if match:
            parts.append(f"## {heading}\n{match.group(1).strip()}")
    if not parts:
        return _clip_text(text, 8000)
    return _clip_text("\n\n".join(parts), 18000)


def _clip_text(text: str, limit: int) -> str:
    # 防止 profile、技能文档或日志片段撑爆模型上下文。
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def _tail_text(text: Any, limit: int = 1200) -> str:
    # 日志里只保留尾部，通常错误原因和最终输出都在末尾。
    value = str(text or "")
    return value[-limit:] if len(value) > limit else value


def _tool_result_log(result: ToolResult) -> dict[str, Any]:
    # 工具结果日志只记录摘要和尾部，避免把完整 HTML 或命令输出塞进事件日志。
    return {
        "id": result.id,
        "name": result.name,
        "ok": result.ok,
        "artifacts": result.artifacts,
        "output_tail": _tail_text(result.output, 2000),
        "error_tail": _tail_text(result.error, 2000),
    }


def _plan_log(plan: TimelinePlan) -> dict[str, Any]:
    # 计划日志保留核心字段和前几个 slot，便于快速定位时间轴问题。
    return {
        "title": plan.title,
        "format": plan.format,
        "width": plan.width,
        "height": plan.height,
        "duration": plan.duration,
        "slot_count": len(plan.slots),
        "slots": [
            {
                "id": slot.id,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "source_asset_id": slot.source_asset_id,
                "media_start": slot.media_start,
                "playback_rate": slot.playback_rate,
                "role": slot.role,
                "visual_fallback_text": _clip_text(slot.visual_fallback_text, 120),
                "transition": slot.transition,
            }
            for slot in plan.slots[:12]
        ],
    }


def _revision_context_log(context: Any) -> dict[str, Any]:
    if not isinstance(context, dict) or not context:
        return {}
    return {
        "parent_job_id": context.get("parent_job_id"),
        "base_job_id": context.get("base_job_id"),
        "revision_index": context.get("revision_index"),
        "instruction": _clip_text(str(context.get("instruction") or ""), 300),
        "history_count": len(context.get("history") or []) if isinstance(context.get("history"), list) else 0,
    }


def _analysis_asset_log(analysis: AnalysisBundle) -> list[dict[str, Any]]:
    # phase2 启动日志只需要素材概览，不记录完整分析对象。
    rows = []
    for asset in [*analysis.samples, *analysis.assets]:
        meta = None
        if asset.video:
            meta = asset.video.meta
        elif asset.audio:
            meta = asset.audio.meta
        elif asset.image:
            meta = asset.image.meta
        rows.append(
            {
                "id": asset.id,
                "role": asset.role,
                "kind": asset.kind.value if isinstance(asset.kind, MediaKind) else str(asset.kind),
                "path": asset.path,
                "duration": getattr(meta, "duration", None) if meta else None,
                "width": getattr(meta, "width", None) if meta else None,
                "height": getattr(meta, "height", None) if meta else None,
                "has_audio": getattr(meta, "has_audio", False) if meta else False,
                "has_video": getattr(meta, "has_video", False) if meta else False,
            }
        )
    return rows


def _analysis_for_script(analysis: AnalysisBundle) -> dict[str, Any]:
    # 给脚本 Writer 的分析摘要保留样例和用户素材，方便判断素材缺口和 demo 替代方案。
    def asset_summary(asset: Any) -> dict[str, Any]:
        meta = None
        video_parts: list[dict[str, Any]] = []
        music_parts: list[dict[str, Any]] = []
        asr_parts: list[dict[str, Any]] = []
        if asset.video:
            meta = asset.video.meta
            video_parts = [to_plain(part) for part in asset.video.parts]
        elif asset.audio:
            meta = asset.audio.meta
        elif asset.image:
            meta = asset.image.meta
        if asset.audio and asset.audio.music:
            music_parts = [to_plain(part) for part in asset.audio.music.parts]
        if asset.audio and asset.audio.asr:
            asr_parts = [to_plain(part) for part in asset.audio.asr.parts]
        summary = {
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
            "notes": list(getattr(asset, "notes", []) or []),
        }
        if asset.image:
            summary["image_description"] = asset.image.description
            summary["image_visual_style"] = asset.image.visual_style
            summary["image_suggested_use"] = asset.image.suggested_use
        return summary

    return {
        "job_id": analysis.job_id,
        "target_requirement": analysis.target_requirement,
        "struct_info": analysis.struct_info,
        "samples": [asset_summary(asset) for asset in analysis.samples],
        "selected_knowledge_profile_ids": list(analysis.selected_knowledge_profile_ids or []),
        "knowledge_selection_reason": analysis.knowledge_selection_reason,
        "user_assets": [asset_summary(asset) for asset in analysis.assets],
        "notes": list(analysis.notes or []),
        "errors": list(analysis.errors or []),
    }


def _analysis_for_compiler(
    analysis: AnalysisBundle,
    knowledge_profiles: list[dict[str, Any]],
    revision_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # 单样例时给主 Agent 更完整的样例分析；多样例时仍只给合并后的 struct_info，避免参考互相干扰。
    compiler_analysis = {
        "job_id": analysis.job_id,
        "target_requirement": analysis.target_requirement,
        "struct_info": analysis.struct_info,
        "sample_count": len(analysis.samples),
        "has_sample_struct_info": bool(str(analysis.struct_info or "").strip()),
        "sample_assets": [_compiler_asset_summary(analysis.samples[0])] if len(analysis.samples) == 1 else [],
        "selected_knowledge_profiles": [
            {
                "id": str(profile.get("id") or ""),
                "summary": str(profile.get("summary") or ""),
                "struct_info": str(profile.get("struct_info") or ""),
            }
            for profile in knowledge_profiles
        ],
        "user_assets": [_compiler_asset_summary(asset) for asset in analysis.assets],
        "notes": list(analysis.notes or []),
        "errors": list(analysis.errors or []),
    }
    compact_revision = _revision_context_for_compiler(revision_context or {})
    if compact_revision:
        compiler_analysis["revision_context"] = compact_revision
    return compiler_analysis


def _revision_context_for_compiler(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict) or not context:
        return {}
    previous = context.get("previous") if isinstance(context.get("previous"), dict) else {}
    previous_plan = previous.get("plan") if isinstance(previous.get("plan"), dict) else {}
    compact_plan = {
        key: value
        for key, value in previous_plan.items()
        if key != "raw_agent"
    }
    history = context.get("history") if isinstance(context.get("history"), list) else []
    return {
        "parent_job_id": str(context.get("parent_job_id") or ""),
        "base_job_id": str(context.get("base_job_id") or ""),
        "revision_index": context.get("revision_index"),
        "instruction": str(context.get("instruction") or ""),
        "previous": {
            "job_id": str(previous.get("job_id") or ""),
            "plan": compact_plan,
            "video_script": _clip_text(str(previous.get("video_script") or ""), 5000),
            "output": str(previous.get("output") or ""),
        },
        "history": history[-8:],
    }


def _compiler_asset_summary(asset: AssetIR) -> dict[str, Any]:
    # 给主 Agent 的素材摘要保留剪辑决策需要的信息：时长、完整画面片段、声音和 ASR。
    meta = None
    video_parts: list[dict[str, Any]] = []
    music_parts: list[dict[str, Any]] = []
    asr_parts: list[dict[str, Any]] = []
    if asset.video:
        meta = asset.video.meta
        video_parts = [to_plain(part) for part in asset.video.parts]
    elif asset.audio:
        meta = asset.audio.meta
    elif asset.image:
        meta = asset.image.meta
    if asset.audio and asset.audio.music:
        music_parts = [to_plain(part) for part in asset.audio.music.parts]
    if asset.audio and asset.audio.asr:
        asr_parts = [to_plain(part) for part in asset.audio.asr.parts]
    summary: dict[str, Any] = {
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
        summary["image_description"] = asset.image.description
        summary["image_visual_style"] = asset.image.visual_style
        summary["image_suggested_use"] = asset.image.suggested_use
    return summary


def _analysis_has_tts_for_slot(analysis: AnalysisBundle, slot_id: str, text: str) -> bool:
    # 只按文本 hash 复用 TTS，避免 revision 中 slot id 相同但旁白已变化时误用旧音频。
    expected_hash = _text_sha1(text)
    expected_text = f"tts_text_sha1={expected_hash}"
    for asset in analysis.assets:
        notes = set(asset.notes or [])
        if "generated_tts=true" not in notes:
            continue
        if expected_text in notes:
            return True
    return False


def _next_tts_asset_id(analysis: AnalysisBundle) -> str:
    # 自动生成连续的 asset_tts_N，跳过已存在的 TTS 素材 id。
    existing = {asset.id for asset in analysis.assets}
    idx = 1
    while f"asset_tts_{idx}" in existing:
        idx += 1
    return f"asset_tts_{idx}"


def _safe_generated_asset_id(value: str) -> str:
    # 生成素材 id 只能包含安全字符，后续会同时用于文件名。
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return text or "asset_tts"


def _unique_asset_id(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    idx = 2
    while f"{base}_{idx}" in existing:
        idx += 1
    return f"{base}_{idx}"


def _text_sha1(text: str) -> str:
    return hashlib.sha1(str(text or "").encode("utf-8")).hexdigest()


def _int_range(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except Exception:
        number = default
    return max(minimum, min(maximum, number))


def _append_generated_tts_manifest(job_dir: Path, row: dict[str, Any]) -> None:
    # 额外维护一份 TTS manifest，便于前端或排障时查看哪些旁白是自动生成的。
    path = job_dir / "generated_tts_manifest.json"
    existing = read_json(path)
    rows = existing if isinstance(existing, list) else []
    rows.append(row)
    write_json(path, rows)


def _retryable_ark_error(exc: Exception) -> bool:
    # 当前只把限流/频率类错误视为可重试，避免对内容或参数错误做无意义重试。
    text = str(exc)
    return "429" in text or "RequestBurstTooFast" in text or "rate" in text.lower()


def _agent_instructions() -> str:
    return AGENT_INSTRUCTIONS


def _hyperframes_instructions() -> str:
    return HYPERFRAMES_SUBAGENT_INSTRUCTIONS


# 清洗 LLM 返回的时间轴计划：
# 1. 校验 plan 必须是对象，且 phase2 必须有用户素材可用。
# 2. 兼容 slots/timeline/scenes 等不同字段名，并逐个归一化为 TimelineSlot。
# 3. 拒绝把 sample_* 样例素材写入 source_asset_id，样例只能作为结构参考。
# 4. duration 缺失或非法时，从所有 slot 的最大 end_time 推导；仍非法则报错。
# 5. 补齐标题、画幅、尺寸、包装、音频策略、缺失素材等字段，最终构造强类型 TimelinePlan。
def _timeline_plan_from_agent(value: Any, analysis: AnalysisBundle) -> TimelinePlan:
    if not isinstance(value, dict):
        raise TypeError("agent plan must be an object")
    if not analysis.assets:
        raise ValueError("analysis must include at least one user asset for phase2")

    known_assets = {asset.id: asset.path for asset in analysis.assets}
    sample_ids = {asset.id for asset in analysis.samples}
    raw_slots = value.get("slots") or value.get("timeline") or value.get("scenes") or []
    slots: list[TimelineSlot] = []
    if isinstance(raw_slots, list):
        for idx, item in enumerate(raw_slots):
            if not isinstance(item, dict):
                continue
            slot = _timeline_slot_from_agent(item, idx, known_assets)
            if slot:
                slots.append(slot)
    if not slots:
        raise ValueError("agent plan must include at least one valid slot")
    if any(str(slot.source_asset_id or "").startswith("sample") or slot.source_asset_id in sample_ids for slot in slots):
        # 样例只允许作为结构参考，绝不能出现在最终成片素材引用里。
        raise ValueError("agent plan must not use samples as source_asset_id; samples are reference-only")

    duration = _number_value(value.get("duration"), 0.0)
    if duration <= 0:
        duration = max(slot.end_time for slot in slots)
    if duration <= 0:
        raise ValueError("agent plan duration must be positive")

    plan_data = {
        "title": str(value.get("title") or analysis.target_requirement or "SakugaCut Structure Transfer"),
        "format": value.get("format") if value.get("format") in {"vertical", "horizontal"} else "vertical",
        "width": int(_number_value(value.get("width"), 1080)),
        "height": int(_number_value(value.get("height"), 1920)),
        "duration": round(duration, 2),
        "slots": slots,
        "gaps": value.get("gaps") if isinstance(value.get("gaps"), list) else [],
        "packaging": value.get("packaging") or value.get("packaging_style") or {},
        "audio_strategy": value.get("audio_strategy") or {},
        "explanation": str(value.get("explanation") or value.get("notes") or ""),
        "missing_assets": value.get("missing_assets") if isinstance(value.get("missing_assets"), list) else [],
    }
    return TimelinePlan(**plan_data)


def _timeline_slot_from_agent(item: dict[str, Any], idx: int, known_assets: dict[str, str]) -> TimelineSlot | None:
    # 兼容多种字段别名，尽量把模型输出归一化为稳定 slot。
    start = _number_value(item.get("start_time", item.get("start")), 0.0)
    end = _number_value(item.get("end_time", item.get("end")), start + 1.0)
    if end <= start:
        end = start + 1.0

    asset_id = item.get("source_asset_id") or item.get("asset_id")
    if isinstance(item.get("asset"), str) and item["asset"] in known_assets:
        asset_id = item["asset"]
    ref_id, ref_start = _parse_asset_ref(item.get("asset_ref") or item.get("source_ref") or item.get("media_ref"), known_assets)
    if not asset_id and ref_id:
        # 支持 asset_1#3.5 这类紧凑引用，便于模型同时表达素材和取用起点。
        asset_id = ref_id

    media_start = _number_value(item.get("media_start", item.get("source_start")), ref_start or 0.0)
    source_path = known_assets.get(str(asset_id)) if asset_id else None
    role = str(item.get("role") or item.get("editing_role") or item.get("scene_role") or "")
    onscreen_text = str(item.get("onscreen_text") or item.get("content") or item.get("text") or item.get("caption") or "")
    notes = str(item.get("notes") or item.get("visual_style") or item.get("description") or "")

    return TimelineSlot(
        id=str(item.get("id") or f"slot_{idx + 1}"),
        start_time=round(start, 2),
        end_time=round(end, 2),
        source_asset_id=str(asset_id) if asset_id else None,
        source_path=source_path,
        media_start=round(media_start, 2),
        playback_rate=_playback_rate_value(item.get("playback_rate")),
        role=role,
        onscreen_text=onscreen_text,
        visual_fallback_text=str(item.get("visual_fallback_text") or ""),
        narration=str(item.get("narration") or item.get("voiceover") or ""),
        transition=str(item.get("transition") or ("cut" if idx == 0 else "match_cut")),
        notes=notes,
    )


def _has_user_visual_assets(analysis: AnalysisBundle) -> bool:
    return any(asset.kind in {MediaKind.video, MediaKind.image} for asset in analysis.assets)


def _parse_asset_ref(value: Any, known_assets: dict[str, str]) -> tuple[str | None, float | None]:
    # 解析类似 asset_1#12.3 的引用，返回素材 id 和源素材起始秒数。
    text = str(value or "").strip()
    if not text:
        return None, None
    asset_part, _, range_part = text.partition("#")
    asset_id = asset_part.strip()
    if asset_id not in known_assets:
        asset_id = next((known for known in known_assets if known and known in text), "")
    numbers = re.findall(r"\d+(?:\.\d+)?", range_part)
    media_start = float(numbers[0]) if numbers else None
    return (asset_id or None), media_start


def _number_value(value: Any, default: float) -> float:
    # 数值字段同时兼容数字、带单位字符串和 mm:ss/hh:mm:ss 格式。
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return float(default)
    if ":" in text:
        parts = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return float(default)
    try:
        return float(match.group(0))
    except ValueError:
        return float(default)


def _playback_rate_value(value: Any) -> float:
    rate = _number_value(value, 1.0)
    if rate <= 0:
        rate = 1.0
    return round(max(0.25, min(4.0, rate)), 3)


def _speed_variant_argv(src: Path, out_path: Path, media_start: float, source_duration: float, rate: float, has_audio: bool) -> list[str]:
    argv = [
        "ffmpeg",
        "-y",
        "-ss",
        _ffmpeg_number(max(0.0, media_start)),
        "-t",
        _ffmpeg_number(source_duration),
        "-i",
        str(src),
        "-map",
        "0:v:0",
    ]
    if has_audio:
        argv.extend(["-map", "0:a:0?", "-filter:a", _atempo_filter(rate), "-c:a", "aac", "-b:a", "192k"])
    else:
        argv.append("-an")
    argv.extend(
        [
            "-filter:v",
            f"setpts=PTS/{_ffmpeg_number(rate)}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
    )
    return argv


def _atempo_filter(rate: float) -> str:
    parts: list[float] = []
    value = rate
    while value < 0.5:
        parts.append(0.5)
        value /= 0.5
    while value > 100:
        parts.append(100.0)
        value /= 100.0
    parts.append(value)
    return ",".join(f"atempo={_ffmpeg_number(part)}" for part in parts)


def _ffmpeg_number(value: float) -> str:
    return f"{float(value):.6g}"


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "")).strip("_") or "asset"


def _extract_response_html(parsed: Any, raw: str) -> str:
    # 子 Agent 可能按 JSON、Markdown fenced code 或裸 HTML 返回；这里统一提取完整 HTML。
    if isinstance(parsed, dict):
        for key in ("html", "index_html", "index.html"):
            value = parsed.get(key)
            if isinstance(value, str) and "<html" in value.lower():
                return value.strip()
    fenced = re.search(r"```html\s*([\s\S]*?)```", raw or "", re.IGNORECASE)
    if fenced and "<html" in fenced.group(1).lower():
        return fenced.group(1).strip()
    match = re.search(r"(<!doctype html[\s\S]*?</html>)", raw or "", re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"(<html[\s\S]*?</html>)", raw or "", re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _media_src_entries(text: str) -> list[dict[str, str]]:
    # 扫描 HTML 中的媒体标签，用于校验素材 src 是否都来自复制后的 assets/ 目录。
    entries: list[dict[str, str]] = []
    for match in re.finditer(r"<(video|audio|img)\b([^>]*)>", text, re.IGNORECASE | re.DOTALL):
        tag = match.group(1).lower()
        attrs = match.group(2)
        src_match = re.search(r"\bsrc\s*=\s*(['\"])(.*?)\1", attrs, re.IGNORECASE | re.DOTALL)
        if src_match:
            entries.append({"tag": tag, "attrs": attrs, "src": src_match.group(2)})
    return entries


def _root_composition_attrs(text: str) -> str:
    # 找到根 composition 元素属性，检查 standalone HyperFrames 必需的 data-* 字段。
    match = re.search(
        r"<[A-Za-z][\w:-]*\b([^>]*\bdata-composition-id\s*=\s*(['\"])[^'\"]+\2[^>]*)>",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    return match.group(1) if match else ""


def _timed_non_root_entries(text: str) -> list[dict[str, str]]:
    # 提取带 data-start/data-duration 的非根元素，确保它们都能被 clip 可见性规则控制。
    entries: list[dict[str, str]] = []
    for match in re.finditer(r"<([A-Za-z][\w:-]*)\b([^>]*(?:\bdata-start\b|\bdata-duration\b)[^>]*)>", text, re.IGNORECASE | re.DOTALL):
        tag = match.group(1).lower()
        attrs = match.group(2)
        if "data-composition-id" in attrs:
            continue
        id_match = re.search(r"\bid\s*=\s*(['\"])(.*?)\1", attrs, re.IGNORECASE | re.DOTALL)
        entries.append({"tag": tag, "attrs": attrs, "id": id_match.group(2) if id_match else ""})
    return entries


def _hyperframes_lint_has_warnings(output: str) -> bool:
    # 有些 warning 已知不阻塞交付，其余 lint warning 在严格门禁里按失败处理。
    non_blocking = {"timeline_track_too_dense"}
    for line in (output or "").splitlines():
        if "⚠" not in line:
            continue
        if any(code in line for code in non_blocking):
            continue
        return True
    return False


def _src_path_part(src: str) -> str:
    # 校验媒体路径时去掉 query/hash，并解码 URL 转义。
    return unquote(str(src).split("?", 1)[0].split("#", 1)[0])


def _collect_known_asset_ids(value: Any, known_ids: set[str]) -> set[str]:
    # 从嵌套字符串/list/dict 中递归找出已知 asset id，兼容模型输出的多种写法。
    found: set[str] = set()
    if isinstance(value, str):
        if value in known_ids:
            found.add(value)
    elif isinstance(value, list):
        for item in value:
            found.update(_collect_known_asset_ids(item, known_ids))
    elif isinstance(value, dict):
        for item in value.values():
            found.update(_collect_known_asset_ids(item, known_ids))
    return found


def _html_has_audio_tag(path: Path) -> bool:
    # 快速判断 HTML 是否声明过音频，用来和渲染后的 mp4 音频流做一致性检查。
    if not path.exists():
        return False
    return bool(re.search(r"<audio\b", path.read_text(encoding="utf-8"), re.IGNORECASE))


def _mp4_has_audio(path: Path) -> bool:
    # 用 ffprobe 检查输出文件是否真的包含音频流，而不是只看文件是否渲染成功。
    result = run_cmd(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "json",
            str(path),
        ],
        timeout=60,
    )
    if not result["ok"]:
        return False
    try:
        data = json.loads(result.get("stdout") or "{}")
    except json.JSONDecodeError:
        return False
    return bool(data.get("streams"))


def _ffmpeg_output_candidate(args: dict[str, Any], argv: list[str], job_dir: Path, *, must_exist: bool = False) -> Path | None:
    # 推断 ffmpeg 输出路径，并强制它位于当前 job 目录内，避免工具写到外部路径。
    output_value = str(args.get("output_path") or "").strip()
    if output_value:
        candidate = Path(output_value)
    elif argv and argv[0] == "ffmpeg" and len(argv) >= 2 and not argv[-1].startswith("-"):
        candidate = Path(argv[-1])
    else:
        return None
    if not candidate.is_absolute():
        candidate = job_dir / candidate
    try:
        resolved = candidate.resolve()
        root = job_dir.resolve()
    except Exception:
        return None
    if resolved != root and root not in resolved.parents:
        return None
    if must_exist and not resolved.exists():
        return None
    return resolved


def _replace_analysis_asset_path(analysis: AnalysisBundle, asset_id: str, replacement: Path) -> bool:
    # ffmpeg 预处理生成替代素材后，同步更新 analysis 中的路径和媒体元信息。
    for asset in [*analysis.samples, *analysis.assets]:
        if asset.id != asset_id:
            continue
        asset.path = str(replacement)
        asset.kind = detect_kind(replacement)
        note = f"source_replaced_by_ffmpeg={replacement}"
        if note not in asset.notes:
            asset.notes.append(note)
        if asset.video:
            asset.video.meta = ffprobe(replacement)
        elif asset.audio:
            asset.audio.meta = ffprobe(replacement)
        elif asset.image:
            asset.image.meta = ffprobe(replacement)
        return True
    return False


def _job_relative_path(job_dir: Path, path: Path) -> str:
    # artifact 记录优先使用 job 相对路径，方便前端或下载接口定位文件。
    try:
        return str(path.resolve().relative_to(job_dir.resolve()))
    except Exception:
        return str(path)


def _tool_calls(value: Any) -> list[ToolCall]:
    # 归一化不同来源的工具调用：原生对象、dict、list、字符串参数都统一转 ToolCall。
    calls: list[ToolCall] = []
    if not value:
        return calls
    if isinstance(value, ToolCall):
        return [value]
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return calls
    for item in value:
        if isinstance(item, ToolCall):
            calls.append(item)
            continue
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("tool")
        if not name:
            continue
        args = item.get("arguments") or item.get("args") or {}
        if isinstance(args, str):
            parsed = extract_json(args)
            args = parsed if isinstance(parsed, dict) else {"command": args}
        calls.append(ToolCall(id=str(item.get("id") or uuid.uuid4().hex[:8]), name=str(name), arguments=args))
    return calls


def _merge_tool_calls(*groups: list[ToolCall]) -> list[ToolCall]:
    # 合并原生和旧版工具调用时按 name+arguments 去重，避免同一工具被执行两次。
    merged: list[ToolCall] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        for call in group:
            key = (call.name, json.dumps(call.arguments, ensure_ascii=False, sort_keys=True))
            if key in seen:
                continue
            seen.add(key)
            merged.append(call)
    return merged


def _normalize_hyperframes_argv(argv: list[str]) -> tuple[list[str], str]:
    # 接受模型写的 npx hyperframes 形式，但统一改成配置里的 hyperframes 包调用。
    if len(argv) >= 3 and argv[0] == "npx" and argv[1] == "hyperframes":
        return _hyperframes_argv(*argv[2:]), argv[2]
    if len(argv) >= 4 and argv[0] == "npx" and argv[1] == "--yes" and argv[2].startswith("hyperframes"):
        return _hyperframes_argv(*argv[3:]), argv[3]
    return [], ""


def _hyperframes_argv(*args: str) -> list[str]:
    # 所有 HyperFrames CLI 调用都从这里生成，便于通过配置切换包名或版本。
    package = str(settings.hyperframes_package or "hyperframes").strip() or "hyperframes"
    return ["npx", "--yes", package, *[str(arg) for arg in args]]


def _project_aware_hyperframes_command(cwd: Path, argv: list[str], subcommand: str) -> tuple[Path, list[str]]:
    # 对已初始化项目，在仓库根运行 CLI 并显式传项目路径，兼容 HyperFrames 的项目参数规则。
    if subcommand == "init" or not (cwd / "hyperframes.json").exists():
        return cwd, argv
    sub_idx = 3 if len(argv) >= 4 and argv[1] == "--yes" else 2
    tail = argv[sub_idx + 1 :]
    has_project_arg = bool(tail and not tail[0].startswith("-"))
    if has_project_arg:
        return settings.root, argv
    return settings.root, [*argv[: sub_idx + 1], str(cwd), *tail]
