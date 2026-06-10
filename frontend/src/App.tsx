import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { BookOpen, CheckSquare, ChevronDown, ChevronUp, Database, FileJson, FileText, Film, FolderOpen, GitBranch, MessageSquare, Play, RefreshCw, Square, Trash2, Upload } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type JobStatus = {
  job_id: string;
  state: string;
  created_at?: string;
  updated_at?: string;
  progress: string[];
  artifacts: Record<string, string>;
  artifact_urls: Record<string, string>;
  error?: string | null;
  parent_job_id?: string | null;
  base_job_id?: string;
  revision_instruction?: string;
  revision_index?: number | null;
};

type RunSummary = JobStatus & {
  sample_name?: string;
  sample_names?: string[];
  asset_count?: number;
  target_requirement?: string;
  mtime?: number;
};

type KnowledgeProfile = {
  id: string;
  summary: string;
  source_video_name: string;
  created_at: string;
};

type KnowledgeProfileDetail = KnowledgeProfile & {
  struct_info: string;
  source_video_path: string;
};

const API = "";

export function App() {
  const [activePage, setActivePage] = useState<"create" | "knowledge">("create");
  const [samples, setSamples] = useState<File[]>([]);
  const [assets, setAssets] = useState<File[]>([]);
  const [targetRequirement, setTargetRequirement] = useState("");
  const [knowledgeProfiles, setKnowledgeProfiles] = useState<KnowledgeProfile[]>([]);
  const [selectedProfileIds, setSelectedProfileIds] = useState<string[]>([]);
  const [expandedProfileIds, setExpandedProfileIds] = useState<string[]>([]);
  const [profileDetails, setProfileDetails] = useState<Record<string, KnowledgeProfileDetail>>({});
  const [profileDetailsLoadingIds, setProfileDetailsLoadingIds] = useState<string[]>([]);
  const [profileDetailsErrors, setProfileDetailsErrors] = useState<Record<string, string>>({});
  const [knowledgeVideo, setKnowledgeVideo] = useState<File | null>(null);
  const [knowledgeSummary, setKnowledgeSummary] = useState("");
  const [knowledgeBusy, setKnowledgeBusy] = useState(false);
  const [knowledgeError, setKnowledgeError] = useState("");
  const [job, setJob] = useState<JobStatus | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [analysis, setAnalysis] = useState<unknown>(null);
  const [plan, setPlan] = useState<unknown>(null);
  const [revisionContext, setRevisionContext] = useState<unknown>(null);
  const [videoScript, setVideoScript] = useState("");
  const [revisionInstruction, setRevisionInstruction] = useState("");
  const [revisionBusy, setRevisionBusy] = useState(false);
  const [revisionError, setRevisionError] = useState("");
  const [busy, setBusy] = useState(false);
  const [runsLoading, setRunsLoading] = useState(false);
  const timer = useRef<number | null>(null);

  const outputUrl = useMemo(() => job?.artifact_urls?.output, [job]);
  const structInfo = useMemo(() => getStructInfo(analysis), [analysis]);
  const selectedProfileIdSet = useMemo(() => new Set(selectedProfileIds), [selectedProfileIds]);
  const baseJobId = useMemo(() => job ? (job.base_job_id || job.job_id) : "", [job]);
  const versionRuns = useMemo(() => collectVersionRuns(runs, job, baseJobId), [runs, job, baseJobId]);
  const canRun = Boolean(assets.length && !busy);
  const canRevise = Boolean(job?.job_id && job.state === "done" && revisionInstruction.trim() && !revisionBusy && !busy);

  useEffect(() => {
    loadRuns();
    loadKnowledgeProfiles();
  }, []);

  useEffect(() => {
    if (!job?.job_id) return;
    if (timer.current) window.clearInterval(timer.current);
    if (["done", "error"].includes(job.state)) return;
    timer.current = window.setInterval(() => refresh(job.job_id), 1800);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [job?.job_id, job?.state]);

  useEffect(() => {
    if (!job) return;
    if (["done", "error"].includes(job.state)) setBusy(false);
    if (job.artifacts?.analysis) loadJson(job.job_id, "analysis", setAnalysis);
    if (job.artifacts?.plan) loadJson(job.job_id, "plan", setPlan);
    if (job.artifacts?.revision_context) {
      loadJson(job.job_id, "revision_context", setRevisionContext);
    } else {
      setRevisionContext(null);
    }
    if (job.artifact_urls?.video_script) loadText(job.artifact_urls.video_script, setVideoScript);
    if (["done", "error"].includes(job.state)) loadRuns();
  }, [job]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!assets.length) return;
    setBusy(true);
    setAnalysis(null);
    setPlan(null);
    setRevisionContext(null);
    setVideoScript("");
    setRevisionError("");

    const form = new FormData();
    samples.forEach((file) => form.append("samples", file));
    assets.forEach((file) => form.append("assets", file));
    selectedProfileIds.forEach((id) => form.append("knowledge_profile_ids", id));
    form.append("target_requirement", targetRequirement);

    const created = await fetch(`${API}/api/jobs`, { method: "POST", body: form }).then((r) => r.json());
    if (created.error) {
      setBusy(false);
      setJob(created);
      return;
    }
    setJob(created);
    await loadRuns();
    await fetch(`${API}/api/jobs/${created.job_id}/run`, { method: "POST" });
    await refresh(created.job_id);
  }

  async function submitRevision(event: FormEvent) {
    event.preventDefault();
    if (!job?.job_id || !revisionInstruction.trim() || revisionBusy) return;
    setRevisionBusy(true);
    setRevisionError("");
    setBusy(true);
    setAnalysis(null);
    setPlan(null);
    setRevisionContext(null);
    setVideoScript("");
    try {
      const created = await fetch(`${API}/api/jobs/${job.job_id}/revisions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction: revisionInstruction.trim() }),
      }).then((r) => r.json());
      if (created.error) {
        setBusy(false);
        setRevisionError(created.error);
        return;
      }
      setRevisionInstruction("");
      setJob(created);
      await loadRuns();
      await refresh(created.job_id);
    } catch (error) {
      setBusy(false);
      setRevisionError(error instanceof Error ? error.message : "修改请求失败");
    } finally {
      setRevisionBusy(false);
    }
  }

  async function refresh(jobId = job?.job_id) {
    if (!jobId) return;
    const next = await fetch(`${API}/api/jobs/${jobId}`).then((r) => r.json());
    setJob(next);
  }

  async function loadRuns() {
    setRunsLoading(true);
    try {
      const data = await fetch(`${API}/api/runs`).then((r) => r.json());
      setRuns(Array.isArray(data.runs) ? data.runs : []);
    } catch {
      setRuns([]);
    } finally {
      setRunsLoading(false);
    }
  }

  async function loadKnowledgeProfiles() {
    try {
      const data = await fetch(`${API}/api/knowledge-profiles`).then((r) => r.json());
      setKnowledgeProfiles(Array.isArray(data.profiles) ? data.profiles : []);
    } catch {
      setKnowledgeProfiles([]);
    }
  }

  async function submitKnowledgeProfile(event: FormEvent) {
    event.preventDefault();
    if (!knowledgeVideo || knowledgeBusy) return;
    setKnowledgeBusy(true);
    setKnowledgeError("");
    const form = new FormData();
    form.append("video", knowledgeVideo);
    form.append("summary", knowledgeSummary);
    try {
      const created = await fetch(`${API}/api/knowledge-profiles`, { method: "POST", body: form }).then((r) => r.json());
      if (created.error) {
        setKnowledgeError(created.error);
      } else {
        setKnowledgeVideo(null);
        setKnowledgeSummary("");
        await loadKnowledgeProfiles();
      }
    } catch (error) {
      setKnowledgeError(error instanceof Error ? error.message : "知识库上传失败");
    } finally {
      setKnowledgeBusy(false);
    }
  }

  async function openRun(jobId: string) {
    setBusy(false);
    setAnalysis(null);
    setPlan(null);
    setRevisionContext(null);
    setVideoScript("");
    setRevisionError("");
    await refresh(jobId);
  }

  function toggleProfileSelection(profileId: string) {
    setSelectedProfileIds((current) => (
      current.includes(profileId)
        ? current.filter((id) => id !== profileId)
        : [...current, profileId]
    ));
  }

  async function toggleProfileDetail(profileId: string) {
    if (expandedProfileIds.includes(profileId)) {
      setExpandedProfileIds((current) => current.filter((id) => id !== profileId));
      return;
    }

    setExpandedProfileIds((current) => [...current, profileId]);
    if (profileDetails[profileId] || profileDetailsLoadingIds.includes(profileId)) return;

    setProfileDetailsLoadingIds((current) => [...current, profileId]);
    setProfileDetailsErrors((current) => ({ ...current, [profileId]: "" }));
    try {
      const detail = await fetch(`${API}/api/knowledge-profiles/${profileId}`).then((r) => r.json());
      if (detail.error) throw new Error(detail.error);
      setProfileDetails((current) => ({ ...current, [profileId]: detail }));
    } catch (error) {
      setProfileDetailsErrors((current) => ({
        ...current,
        [profileId]: error instanceof Error ? error.message : "profile 加载失败",
      }));
    } finally {
      setProfileDetailsLoadingIds((current) => current.filter((id) => id !== profileId));
    }
  }

  function onAssets(event: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files || []);
    setAssets((prev) => mergeFiles(prev, picked));
    event.target.value = "";
  }

  function onSamples(event: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files || []);
    setSamples((prev) => mergeFiles(prev, picked));
    event.target.value = "";
  }

  function removeSample(index: number) {
    setSamples((prev) => prev.filter((_, currentIndex) => currentIndex !== index));
  }

  function removeAsset(index: number) {
    setAssets((prev) => prev.filter((_, currentIndex) => currentIndex !== index));
  }

  return (
    <main className="app">
      <header className="topbar">
        <div>
          <h1>SakugaCut</h1>
          <p>短视频结构迁移与自动剪辑工作台</p>
        </div>
        <div className="topbarActions">
          <button className="iconButton" type="button" onClick={() => loadRuns()}>
            <FolderOpen size={18} />
            加载 runs
          </button>
          <button className="iconButton" type="button" onClick={() => setActivePage("create")}>
            <Film size={18} />
            生成视频
          </button>
          <button className="iconButton" type="button" onClick={() => setActivePage("knowledge")}>
            <Database size={18} />
            知识库
          </button>
          <button className="iconButton" type="button" onClick={() => refresh()} disabled={!job}>
            <RefreshCw size={18} />
            刷新
          </button>
        </div>
      </header>

      {activePage === "knowledge" ? (
        <section className="knowledgePage">
          <form className="panel" onSubmit={submitKnowledgeProfile}>
            <div className="sectionTitle">
              <Upload size={18} />
              添加 Knowledge Profile
            </div>
            <label className="field">
              <span>样例视频</span>
              <input type="file" accept="video/*" onChange={(e) => setKnowledgeVideo(e.target.files?.[0] || null)} />
              <small>{knowledgeVideo?.name || "每次分析 1 条视频"}</small>
            </label>
            <label className="field">
              <span>简介</span>
              <input
                type="text"
                value={knowledgeSummary}
                onChange={(e) => setKnowledgeSummary(e.target.value)}
                placeholder="可留空，由 LLM 生成"
              />
            </label>
            {knowledgeError ? <div className="error">{knowledgeError}</div> : null}
            <button className="primary" disabled={!knowledgeVideo || knowledgeBusy} type="submit">
              <BookOpen size={18} />
              {knowledgeBusy ? "分析中" : "上传并入库"}
            </button>
          </form>

          <section className="panel">
            <div className="runsHeader">
              <div className="sectionTitle">
                <Database size={18} />
                Knowledge Profiles
              </div>
              <button className="iconButton compact" type="button" onClick={loadKnowledgeProfiles}>
                <RefreshCw size={16} />
                重载
              </button>
            </div>
            <div className="profileList">
              {knowledgeProfiles.length ? (
                knowledgeProfiles.map((profile) => (
                  <div className="profileItem" key={profile.id}>
                    <strong>{profile.summary || profile.id}</strong>
                    <span>{profile.source_video_name || profile.id}</span>
                    <small>{formatDate(profile.created_at)}</small>
                  </div>
                ))
              ) : (
                <div className="emptyList">暂无 knowledge profiles</div>
              )}
            </div>
          </section>
        </section>
      ) : (
        <>
      <section className="grid">
        <form className="panel" onSubmit={submit}>
          <div className="sectionTitle">
            <Upload size={18} />
            输入
          </div>
          <label className="field">
            <span>样例视频</span>
            <input type="file" accept="video/*" multiple onChange={onSamples} />
            <SelectedFileList files={samples} emptyText="可为空，可多选样例视频" onRemove={removeSample} />
          </label>
          <label className="field">
            <span>用户素材</span>
            <input type="file" accept="video/*,audio/*,image/*" multiple onChange={onAssets} />
            <SelectedFileList files={assets} emptyText="可多选视频、音频、图片" onRemove={removeAsset} />
          </label>
          <div className="field">
            <span>知识库选择器</span>
            <div className="profilePicker">
              {knowledgeProfiles.length ? (
                knowledgeProfiles.map((profile) => {
                  const selected = selectedProfileIdSet.has(profile.id);
                  const expanded = expandedProfileIds.includes(profile.id);
                  const detail = profileDetails[profile.id];
                  const loading = profileDetailsLoadingIds.includes(profile.id);
                  const error = profileDetailsErrors[profile.id];

                  return (
                    <div className={`profileChoice${selected ? " selected" : ""}`} key={profile.id}>
                      <div className="profileChoiceHeader">
                        <button
                          aria-pressed={selected}
                          className="profileSelectButton"
                          type="button"
                          onClick={() => toggleProfileSelection(profile.id)}
                        >
                          {selected ? <CheckSquare size={17} /> : <Square size={17} />}
                          <span className="profileChoiceText">
                            <strong>{profile.summary || profile.id}</strong>
                            <span>{profile.source_video_name || profile.id}</span>
                            <small>{formatDate(profile.created_at)}</small>
                          </span>
                        </button>
                        <button className="profileExpandButton" type="button" onClick={() => toggleProfileDetail(profile.id)}>
                          {expanded ? <ChevronUp size={17} /> : <ChevronDown size={17} />}
                          {expanded ? "收起" : "查看"}
                        </button>
                      </div>
                      {expanded ? (
                        <div className="profileDetail">
                          {loading ? <div className="profileDetailState">加载中</div> : null}
                          {error ? <div className="profileDetailState errorText">{error}</div> : null}
                          {detail ? (
                            <>
                              <div className="profileMeta">
                                <span>ID</span>
                                <strong>{detail.id}</strong>
                                <span>来源</span>
                                <strong>{detail.source_video_name}</strong>
                                <span>创建</span>
                                <strong>{formatDate(detail.created_at)}</strong>
                                <span>路径</span>
                                <strong>{detail.source_video_path}</strong>
                              </div>
                              <pre>{detail.struct_info}</pre>
                            </>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  );
                })
              ) : (
                <div className="emptyList">暂无 knowledge profiles</div>
              )}
            </div>
            <small>{selectedProfileIds.length ? `已选 ${selectedProfileIds.length} 条` : "留空将自动选择，也可能不选或多选"}</small>
          </div>
          <label className="field">
            <span>目标要求</span>
            <textarea
              value={targetRequirement}
              onChange={(e) => setTargetRequirement(e.target.value)}
              rows={4}
              placeholder="例如：突出新品质感，节奏更快，结尾强化预约 CTA"
            />
            <small>可为空，将作为 Phase 2 的输入之一</small>
          </label>
          <button className="primary" disabled={!canRun} type="submit">
            <Play size={18} />
            {busy ? "运行中" : "上传并生成 MP4"}
          </button>
        </form>

        <section className="panel">
          <div className="sectionTitle">
            <Film size={18} />
            状态
          </div>
          <div className="statusLine">
            <span>Job</span>
            <strong>{job?.job_id || "-"}</strong>
          </div>
          <div className="statusLine">
            <span>State</span>
            <strong>{job?.state || "idle"}</strong>
          </div>
          {job?.error ? <div className="error">{job.error}</div> : null}
          <div className="log">
            {(job?.progress || []).slice().reverse().map((line, idx) => (
              <div key={`${line}-${idx}`}>{line}</div>
            ))}
          </div>
          <div className="artifacts">
            {job?.artifact_urls?.analysis ? <a href={job.artifact_urls.analysis} target="_blank">analysis.json</a> : null}
            {job?.artifact_urls?.knowledge_selection ? <a href={job.artifact_urls.knowledge_selection} target="_blank">knowledge_selection.json</a> : null}
            {job?.artifact_urls?.revision_context ? <a href={job.artifact_urls.revision_context} target="_blank">revision_context.json</a> : null}
            {job?.artifact_urls?.plan ? <a href={job.artifact_urls.plan} target="_blank">plan.json</a> : null}
            {job?.artifact_urls?.video_script ? <a href={job.artifact_urls.video_script} target="_blank">video_script.md</a> : null}
            {job?.artifact_urls?.hyperframes ? <a href={job.artifact_urls.hyperframes} target="_blank">HyperFrames HTML</a> : null}
            {outputUrl ? <a href={outputUrl} target="_blank">output.mp4</a> : null}
          </div>
        </section>

        <section className="panel">
          <div className="runsHeader">
            <div className="sectionTitle">
              <FolderOpen size={18} />
              Runs
            </div>
            <button className="iconButton compact" type="button" onClick={loadRuns}>
              <RefreshCw size={16} />
              {runsLoading ? "加载中" : "重载"}
            </button>
          </div>
          <div className="runList">
            {runs.length ? (
              runs.map((run) => (
                <button
                  className={`runItem${run.job_id === job?.job_id ? " active" : ""}`}
                  key={run.job_id}
                  type="button"
                  onClick={() => openRun(run.job_id)}
                >
                  <strong>{versionLabel(run)} · {run.job_id}</strong>
                  <span>{run.revision_instruction || run.target_requirement || run.sample_name || "未填写目标要求"}</span>
                  <small>
                    {run.state} · {run.asset_count ?? 0} 素材 · {formatDate(run.updated_at)}
                  </small>
                </button>
              ))
            ) : (
              <div className="emptyList">暂无 runs</div>
            )}
          </div>
        </section>
      </section>

      <section className="result">
        <div className="preview">
          <div className="sectionTitle">
            <Film size={18} />
            输出视频
          </div>
          {outputUrl ? <video src={outputUrl} controls /> : <div className="empty">等待 Phase 2 渲染完成</div>}
          <form className="revisionForm" onSubmit={submitRevision}>
            <div className="sectionTitle compactTitle">
              <MessageSquare size={17} />
              继续修改
            </div>
            <textarea
              value={revisionInstruction}
              onChange={(e) => setRevisionInstruction(e.target.value)}
              rows={3}
              placeholder="例如：结尾 CTA 改成关注账号，整体节奏再快一点"
              disabled={!job || job.state !== "done" || revisionBusy}
            />
            {revisionError ? <div className="error">{revisionError}</div> : null}
            <button className="primary" disabled={!canRevise} type="submit">
              <GitBranch size={18} />
              {revisionBusy ? "提交中" : "生成修改版"}
            </button>
          </form>
          {versionRuns.length ? (
            <div className="versionPanel">
              <div className="sectionTitle compactTitle">
                <GitBranch size={17} />
                版本产出
              </div>
              <div className="versionList">
                {versionRuns.map((run) => (
                  <button
                    className={`versionItem${run.job_id === job?.job_id ? " active" : ""}`}
                    key={run.job_id}
                    type="button"
                    onClick={() => openRun(run.job_id)}
                  >
                    <strong>{versionLabel(run)}</strong>
                    <span>{run.revision_instruction || run.target_requirement || "原始生成"}</span>
                    <small>{run.state} · {formatDate(run.updated_at)}</small>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>
        <TextPanel className="structInfoBox" title="Struct Info" text={structInfo} />
        <JsonPanel className="analysisBox" title="Analysis" data={analysis} />
        <JsonPanel className="planBox" title="Plan" data={plan} />
        {revisionContext ? <JsonPanel className="revisionContextBox" title="Revision Context" data={revisionContext} /> : null}
        <MarkdownPanel className="videoScriptBox" title="Video Script" text={videoScript} />
      </section>
        </>
      )}
    </main>
  );
}

function MarkdownPanel({ className = "", title, text }: { className?: string; title: string; text: string }) {
  return (
    <section className={`textBox ${className}`.trim()}>
      <div className="sectionTitle">
        <FileText size={18} />
        {title}
      </div>
      <div className="markdownBody">
        {text ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown> : "暂无"}
      </div>
    </section>
  );
}

function TextPanel({ className = "", title, text }: { className?: string; title: string; text: string }) {
  return (
    <section className={`textBox ${className}`.trim()}>
      <div className="sectionTitle">
        <FileText size={18} />
        {title}
      </div>
      <pre>{text || "暂无"}</pre>
    </section>
  );
}

function JsonPanel({ className = "", title, data }: { className?: string; title: string; data: unknown }) {
  return (
    <section className={`jsonBox ${className}`.trim()}>
      <div className="sectionTitle">
        <FileJson size={18} />
        {title}
      </div>
      <pre>{data ? JSON.stringify(data, null, 2) : "暂无"}</pre>
    </section>
  );
}

function SelectedFileList({
  files,
  emptyText,
  onRemove,
}: {
  files: File[];
  emptyText: string;
  onRemove: (index: number) => void;
}) {
  if (!files.length) return <small>{emptyText}</small>;

  return (
    <div className="selectedFileList">
      {files.map((file, index) => (
        <div className="selectedFileItem" key={fileKey(file)}>
          <span className="selectedFileName" title={file.name}>{file.name}</span>
          <small className="selectedFileMeta">{formatFileSize(file.size)}</small>
          <button
            aria-label={`删除 ${file.name}`}
            className="fileRemoveButton"
            type="button"
            onClick={() => onRemove(index)}
            title="删除"
          >
            <Trash2 size={15} />
          </button>
        </div>
      ))}
    </div>
  );
}

async function loadText(url: string, setter: (value: string) => void) {
  try {
    const text = await fetch(url).then((r) => (r.ok ? r.text() : ""));
    setter(text);
  } catch {
    // polling will retry
  }
}

async function loadJson(jobId: string, name: string, setter: (value: unknown) => void) {
  try {
    const data = await fetch(`${API}/api/jobs/${jobId}/json/${name}`).then((r) => r.json());
    setter(data);
  } catch {
    // polling will retry
  }
}

function getStructInfo(value: unknown) {
  if (!value || typeof value !== "object") return "";
  const structInfo = (value as { struct_info?: unknown }).struct_info;
  return typeof structInfo === "string" ? structInfo : "";
}

function formatDate(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function collectVersionRuns(runs: RunSummary[], job: JobStatus | null, baseJobId: string) {
  if (!baseJobId) return [];
  const byId = new Map<string, RunSummary>();
  for (const run of runs) {
    if ((run.base_job_id || run.job_id) === baseJobId) {
      byId.set(run.job_id, run);
    }
  }
  if (job && (job.base_job_id || job.job_id) === baseJobId) {
    byId.set(job.job_id, { ...job });
  }
  return Array.from(byId.values()).sort((a, b) => {
    const aIndex = typeof a.revision_index === "number" ? a.revision_index : 0;
    const bIndex = typeof b.revision_index === "number" ? b.revision_index : 0;
    if (aIndex !== bIndex) return aIndex - bIndex;
    return String(a.created_at || "").localeCompare(String(b.created_at || ""));
  });
}

function versionLabel(run: Pick<RunSummary, "revision_index" | "parent_job_id">) {
  const index = typeof run.revision_index === "number" ? run.revision_index : 0;
  return index > 0 || run.parent_job_id ? `修改版 ${index || 1}` : "原版";
}

function mergeFiles(current: File[], picked: File[]) {
  const seen = new Set(current.map(fileKey));
  const merged = [...current];
  for (const file of picked) {
    const key = fileKey(file);
    if (!seen.has(key)) {
      seen.add(key);
      merged.push(file);
    }
  }
  return merged;
}

function fileKey(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function formatFileSize(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  const precision = value >= 10 || unitIndex === 0 ? 0 : 1;
  return `${value.toFixed(precision)} ${units[unitIndex]}`;
}
