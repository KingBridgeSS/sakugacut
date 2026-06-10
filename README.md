# Knowledge数据库构建

用户可以在"知识库"页面上传单个视频，系统会拆解结构并存入知识库。这里的知识库设计类似skills，由profile summary（用户自己写或LLM生成）+profile content组成。下文把这个过程中单个视频总结的“条目”成为knowledge profile。后续视频生成的时候用户可以选择这些profiles（可多选），也可以让LLM自己选。

这里和LLM的交互复用下文视频生成phase 1的逻辑，后文会详细介绍这里先简要说明：输入是视频画面+视频音轨，LLM输出是分段-语义信息和拆解后的信息struct_info。这里的struct_info就作为profile content。

# 视频生成

用户在“生成视频”页面（也是默认进去的页面）可以上传样例视频（可多个,也可以0个）、输入素材（支持多个视频、音频、图片，但是至少有一个）、选择知识库（optional）、填写目标要求（optional）。

## phase 1

phase 1解析用户上传的样例视频和可用素材（包括视频、音频、图片），发送给多模态LLM分段、描述内容。其中除音频外都发给了doubao-seed-2-0-pro-260215，注意到该模型不支持音频分析，故音频文件发送给lite模型，也就是课题组提供的API。

具体来说，系统对有音轨视频材料先ffmpeg分离出音轨，然后视频部分走视频+音频分析，音频部分走音频分析。音频分析的时候，会发送2个LLM请求，一个在提示词上侧重语音（ASR），另一个侧重背景音乐。提示词工程上，系统会让LLM把这些media尽可能地分段，然后每一个part用以下数据结构存储（用format字段规定LLM返回JSON）。这些part就是未来的原子剪辑材料。

```python
class VideoPart(JsonModel):
    start_time: float = 0.0
    end_time: float = 0.0
    description: str = ""
class MusicPart(JsonModel):
    start_time: float = 0.0
    end_time: float = 0.0
    description: str = ""
class ASRPart(JsonModel):
    start_time: float = 0.0
    end_time: float = 0.0
    text: str = ""
# 图片不用分段，直接返回描述
```

之后，系统会把用户上传的样例视频（下面称为samples）的上述结构作为输入，在另一个干净的上下文发送给LLM，让LLM总结提炼结构信息（返回值后文统称为struct_info），也就是本课题的核心“样例结构迁移”。具体而言，提示词里会让LLM按3节组织：

1. 脚本/段落结构  
2. 包装结构 
3. 背景音乐结构/描述

phase 1的最后把这些素材的分段语义信息，连同struct_info，以及这些media的metadata（用ffprobe解析）存入analysis.json，供phase 2使用。

## phase 2

phase 2主要由1个LLM pipeline（下文称为planner）和1个HyperframesAgent组成

### planner

planner是固定pipeline。它以第一步analysis.json和用户选择的knowledges profiles作为LLM的输入（如果用户不选，系统会单独发一次LLM请求选择语义最近似的knowledge profile），输出一个剪辑计划。

但是这里不一定是全量的analysis.json，当用户上传的len(samples)>1的时候，就不会上传任何sample的分段-语义信息，而是让LLM仅依赖struct_info做计划（事实上struct_info是phase 1中对多个samples的总结）。这么做源于在用户上传多个样例视频时，上下文信息爆炸的考虑。

在提示词中，对用户素材缺失有3中补充方式：

1. 素材复用
2. 慢放素材
3. 让 HyperFrames 生成文字信息画面，也就是写入 下面的slot.visual_fallback_text

返回的plan由以下数据结构约束：

```python
class TimelinePlan(JsonModel):
    duration: float = 12.0 # 单位：秒
    slots: list[TimelineSlot] # 见下
    packaging: dict[str, Any] # 字幕、构图、色彩、节奏等包装方向（作为给hyperframes agent的handoffs之一）
    audio_strategy: Any # 逐段音频策略：保留原声、压低原声、替换、静音、TTS 等
    missing_assets: list[str] # 指出用户的素材缺失，提示用户可以补充哪些素材
class TimelineSlot(JsonModel):
    start_time: float
    end_time: float
    source_asset_id: str | None = None
    media_start: float = 0.0 # 这里指的是选中的media开始的时间
    playback_rate: float = 1.0 # 播放速度
    onscreen_text: str = "" # hyperframes生成的文字
    narration: str = "" # TTS/旁白文本
    transition: str = "cut" # 转场方式
    visual_fallback_text: str = "" # 用文字补充缺失的素材
```

planner执行之后，会根据上面plan中audio_strategy里需要生成TTS的地方，调用火山引擎TTS API生成语音，然后落盘。

再之后，planner会把TimelinePlan作为主要的交付数据交给Hyperframes Agent，让其剪辑。

### Hyperframes Agent

Hyperframes Agent是剪辑系统的核心，也是本系统唯一一个有react loop的地方，所以这里称其为"agent"。

系统初始化 HyperFrames 工程、复制用户素材后，正式进入Hyperframes Agent阶段，这一阶段Agent会使用Hyperframes的能力，按照上一部的TimelinePlan剪辑出最终的成片。

Hyperframes Agent每次向LLM发送的上下文包括之前的上下文可使用的素材、TimelinePlan、hyperframes官方的skills。返回则是html。

Hyperframes Agent使用的tool只有exec_hyperframes，它被严格限制只能执行4个命令：

```
npx hyperframes init
npx hyperframes lint
npx hyperframes inspect
npx hyperframes render
```

### 收尾工作

在Hyperframes Agent生成出视频后，系统会做一些合理性检验，此阶段的代码基于实验+vibe coding完成，让code agent自行生成清洗逻辑，这里不做过多赘述。

最后，系统会在一个干净的上下文中，以planner生成的plan和phase 1生成的analysis.json为LLM输入，输出视频的脚本和用户素材的缺失、当前对用户素材缺失的缓解方案。

## revision

系统支持对生成的视频用自然语言继续修改。用户输入对视频的修改意见，系统创建一个新job，复用parent job的phase 1产物analysis.json（recall: 素材和样例的分段-语义信息），重跑一遍phase2。在analysis里加入如下handoff信息：

```json
{
    "parent_job_id": "上一版 job id",
    "base_job_id": "最初版本 job id",
    "revision_index": 1,
    "instruction": "用户本次修改要求",
    "previous": {
        "job_id": "上一版 job id",
        "plan": "上一版 plan",
        "video_script": "上一版 video_script.md，最多 5000 字",
        "output": "output.mp4"
    },
    "history": "最近 8 条历史修改记录"
}
```

重点是plan和用户本次修改要求。phase2生成plan的时候LLM会参考这些信息。

# 运行方式

```bash
pip install -r requirements.txt
npm --prefix frontend install
cp .env.example .env
```

.env文件：

```bash
DOUBAO_SPEECH_KEY=xx # 火山引擎tts
# 接下来是火山引擎豆包大模型API
# 下面两个是用于音视频理解、agent的模型
ARK_API_KEY=xxx 
ARK_MODEL=doubao-seed-2-0-pro-260215
# 下面两个是豆包lite模型，因为pro不支持音频输入所以音频使用lite
ARK_LITE_API_KEY=ark-xxxx
ARK_LITE_MODEL=ep-xxxx
```

然后开两个终端分别启动前后端

```bash
python -m backend.run # 后端，默认http://localhost:5001
npm --prefix frontend run dev # 前端，默认http://localhost:5173
```

浏览器访问 http://localhost:5173

可以访问runs目录查看中间产物和日志等
