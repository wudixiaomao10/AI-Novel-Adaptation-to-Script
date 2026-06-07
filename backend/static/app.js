const sampleText = `林夏推开旧宅大门，发现屋里一片漆黑。她低声问：“有人吗？”
楼上传来脚步声。林夏握紧手电筒，缓慢走上楼梯。
沈砚从阴影中走出，说：“你终于来了。”`;

const HISTORY_KEY = "novel2script.history.v1";
const PROJECTS_KEY = "novel2script.projects.v1";
const SETTINGS_KEY = "novel2script.settings.v1";
const MAX_HISTORY_ITEMS = 20;

const $ = (selector) => document.querySelector(selector);
const DEFAULT_GENERATION_OPTIONS = {
  script_type: "影视剧本",
  style: "悬疑",
  output_language: "中文",
  episodes: 1,
  episode_duration: "3 分钟",
  dialogue_density: "中",
  adaptation_level: "适度改编",
  ending_type: "悬念式",
};

const form = $("#convertForm");
const titleInput = $("#titleInput");
const novelInput = $("#novelInput");
const yamlOutput = $("#yamlOutput");
const jsonOutput = $("#jsonOutput");
const previewPanel = $("#previewPanel");
const charactersPanel = $("#charactersPanel");
const scenesPanel = $("#scenesPanel");
const storyboardPanel = $("#storyboardPanel");
const analyzeButton = $("#analyzeButton");
const convertButton = $("#convertButton");
const importButton = $("#importButton");
const importInlineButton = $("#importInlineButton");
const importProjectButton = $("#importProjectButton");
const novelFileInput = $("#novelFileInput");
const sampleButton = $("#sampleButton");
const clearButton = $("#clearButton");
const copyButton = $("#copyButton");
const storyboardButton = $("#storyboardButton");
const downloadButton = $("#downloadButton");
const saveProjectButton = $("#saveProjectButton");
const newProjectButton = $("#newProjectButton");
const projectSearch = $("#projectSearch");
const projectList = $("#projectList");
const projectCount = $("#projectCount");
const clearHistoryButton = $("#clearHistoryButton");
const historyList = $("#historyList");
const historyCount = $("#historyCount");
const charCount = $("#charCount");
const sceneCount = $("#sceneCount");
const chapterCount = $("#chapterCount");
const beatTotal = $("#beatTotal");
const characterTotal = $("#characterTotal");
const statusMetric = $("#statusMetric");
const inputState = $("#inputState");
const outputState = $("#outputState");
const statusMessage = $("#statusMessage");
const llmBadge = $("#llmBadge");
const llmMode = $("#llmMode");
const llmModel = $("#llmModel");
const modelStatusInput = $("#modelStatusInput");

let currentYaml = "";
let currentScriptData = null;
let currentAnalysis = null;
let currentProjectStatus = "待解析";
let activeTab = "preview";
let activeView = "workbench";
let activeHistoryFilter = "全部";

function readStore(key, fallback = []) {
  try {
    const parsed = JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function writeStore(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

async function apiJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json();
}

function persistProjectToDatabase(project) {
  apiJson("/api/projects", {
    method: "POST",
    body: JSON.stringify(project),
  }).catch(() => {});
}

function deleteProjectFromDatabase(projectId) {
  if (!projectId) return;
  fetch(`/api/projects/${encodeURIComponent(projectId)}`, { method: "DELETE" }).catch(() => {});
}

function persistHistoryToDatabase(entry) {
  apiJson("/api/history", {
    method: "POST",
    body: JSON.stringify(entry),
  }).catch(() => {});
}

function persistSettingsToDatabase(settings) {
  apiJson("/api/settings", {
    method: "PUT",
    body: JSON.stringify({ settings }),
  }).catch(() => {});
}

async function loadDatabaseState() {
  try {
    const [projectsData, historyData, settingsData] = await Promise.all([
      apiJson("/api/projects"),
      apiJson("/api/history"),
      apiJson("/api/settings"),
    ]);
    if (Array.isArray(projectsData.projects) && projectsData.projects.length) {
      writeProjects(projectsData.projects);
    }
    if (Array.isArray(historyData.history) && historyData.history.length) {
      writeHistory(historyData.history);
    }
    if (settingsData.settings && Object.keys(settingsData.settings).length) {
      writeStore(SETTINGS_KEY, { ...readSettings(), ...settingsData.settings });
      applySettings();
    }
  } catch {
    setStatus("数据库未连接，已使用浏览器本地缓存", "is-error");
  }
}

function generationOptions() {
  return { ...DEFAULT_GENERATION_OPTIONS };
}

function applyOptions(options = {}) {
  return { ...DEFAULT_GENERATION_OPTIONS, ...options };
}

function updateWorkspaceMeta() {
  return currentProjectStatus;
}

function setProjectStatus(status) {
  currentProjectStatus = status;
  updateWorkspaceMeta();
}

function estimateStoryUnits(text) {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  const headings = trimmed.match(/(^|\n)\s*(第\s*[0-9零〇一二三四五六七八九十百千万两]+\s*[章节卷回篇].*|Chapter\s+\d+.*)/gi);
  return headings ? headings.length : Math.max(1, trimmed.split(/\n\s*\n/).filter((part) => part.trim()).length);
}

function updateInputMetrics() {
  const text = novelInput.value;
  const units = estimateStoryUnits(text);
  if (chapterCount) chapterCount.textContent = units;
  charCount.textContent = text.replace(/\s/g, "").length;
  inputState.textContent = units >= 1 ? "可生成短篇或章节剧本" : "上传或粘贴要解析的小说";
  inputState.className = units >= 1 ? "is-ready" : "is-error";
  updateWorkspaceMeta();
}

function setStatus(message, mode = "") {
  if (statusMessage) {
    statusMessage.textContent = message;
    statusMessage.className = mode;
  }
  outputState.textContent = message;
  outputState.className = mode;
  statusMetric.textContent = message;
}

async function loadLlmStatus() {
  try {
    const status = await (await fetch("/api/llm/status")).json();
    llmBadge.classList.toggle("is-real", Boolean(status.enabled && status.configured));
    llmBadge.classList.toggle("is-missing", Boolean(status.enabled && !status.configured));
    llmMode.textContent = status.enabled ? "Real LLM" : "Mock";
    llmModel.textContent = status.enabled ? `${status.provider}:${status.model}` : "enhanced";
    if (modelStatusInput) {
      modelStatusInput.value = status.enabled && status.configured ? `真实 LLM：${status.provider}:${status.model}` : "增强 Mock：本地规则生成";
    }
  } catch {
    llmMode.textContent = "LLM";
    llmModel.textContent = "unknown";
    if (modelStatusInput) modelStatusInput.value = "模型状态读取失败";
  }
}

async function decodeNovelFile(file) {
  const buffer = await file.arrayBuffer();
  for (const [encoding, options] of [["utf-8", { fatal: true }], ["gb18030", {}], ["gbk", {}]]) {
    try {
      const text = new TextDecoder(encoding, options).decode(buffer);
      if (text.trim()) return text.replace(/^\uFEFF/, "");
    } catch {}
  }
  throw new Error("无法读取该文件");
}

async function importNovelFile(file) {
  if (!file) return;
  if (!(file.type.startsWith("text/") || /\.(txt|md|text)$/i.test(file.name))) {
    setStatus("请选择 TXT 或 Markdown 小说文件", "is-error");
    return;
  }
  try {
    const text = await decodeNovelFile(file);
    novelInput.value = text;
    if (!titleInput.value.trim() || titleInput.value.trim() === "夜色旧宅") {
      titleInput.value = file.name.replace(/\.[^.]+$/, "").trim() || "未命名小说";
    }
    resetOutput();
    updateInputMetrics();
    setStatus(`已导入：${file.name}`, "is-ready");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "导入失败", "is-error");
  }
}

function parseStats(scriptData, yamlText = "") {
  const scenes = scriptData?.scenes || [];
  const characters = scriptData?.characters || [];
  const beats = scenes.reduce((sum, scene) => sum + (scene.beats?.length || 0), 0);
  if (scriptData) return { scenes: scenes.length, characters: characters.length, beats };
  return {
    scenes: (yamlText.match(/^\s+- id: scene_/gm) || []).length,
    characters: (yamlText.match(/^\s+- id: char_/gm) || []).length,
    beats: (yamlText.match(/^\s+- type:/gm) || []).length,
  };
}

function applyOutputStats(stats) {
  sceneCount.textContent = stats.scenes;
  characterTotal.textContent = stats.characters;
  if (beatTotal) beatTotal.textContent = stats.beats;
}

async function analyzeNovel() {
  updateInputMetrics();
  const title = titleInput.value.trim();
  const novelText = novelInput.value.trim();
  if (!title || !novelText) return setStatus("作品名称和正文不能为空", "is-error");

  analyzeButton.disabled = true;
  setStatus("解析中", "is-working");
  try {
    const response = await fetch("/api/novel/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, novel_text: novelText }),
    });
    const analysis = await response.json();
    if (!response.ok) throw new Error(analysis.detail || "解析失败");

    currentAnalysis = analysis;
    currentScriptData = null;
    currentYaml = analysis.structure_yaml || "";
    renderAnalysisResult(analysis);
    const stats = { scenes: analysis.scenes?.length || 0, characters: analysis.characters?.length || 0, beats: 0 };
    applyOutputStats(stats);
    maybeSaveHistory({ title, yaml: currentYaml, scriptData: null, analysis, stats, options: generationOptions(), type: "解析小说" });
    saveCurrentProject("已解析");
    setProjectStatus("已解析");
    switchTab("preview");
    setStatus("解析完成，可确认后生成剧本", "is-ready");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "解析失败", "is-error");
  } finally {
    analyzeButton.disabled = false;
  }
}

async function convertNovel(event) {
  event.preventDefault();
  updateInputMetrics();
  const title = titleInput.value.trim();
  const novelText = novelInput.value.trim();
  if (!title || !novelText) return setStatus("作品名称和正文不能为空", "is-error");

  convertButton.disabled = true;
  setStatus("生成中", "is-working");
  try {
    const payload = { title, novel_text: novelText, ...generationOptions() };
    const response = await fetch("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "生成失败");

    currentYaml = data.script_yaml;
    currentScriptData = data.script_data || null;
    currentAnalysis = null;
    renderResult(currentScriptData, currentYaml);
    const stats = parseStats(currentScriptData, currentYaml);
    applyOutputStats(stats);
    maybeSaveHistory({ title, yaml: currentYaml, scriptData: currentScriptData, stats, options: generationOptions(), type: "剧本生成" });
    saveCurrentProject("剧本已生成");
    setProjectStatus("剧本已生成");
    setStatus("生成完成，已保存历史", "is-ready");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "生成失败", "is-error");
  } finally {
    convertButton.disabled = false;
  }
}

function renderResult(scriptData, yamlText) {
  yamlOutput.textContent = yamlText || "";
  jsonOutput.textContent = scriptData ? JSON.stringify(scriptData, null, 2) : "";
  previewPanel.innerHTML = renderPreview(scriptData);
  charactersPanel.innerHTML = renderCharacters(scriptData);
  scenesPanel.innerHTML = renderScenes(scriptData);
  storyboardPanel.innerHTML = renderStoryboard(scriptData);
}

function renderAnalysisResult(analysis) {
  const characters = analysis?.characters || [];
  const scenes = analysis?.scenes || [];
  yamlOutput.textContent = analysis?.structure_yaml || "";
  jsonOutput.textContent = JSON.stringify(analysis || {}, null, 2);
  previewPanel.innerHTML = `
    <section class="analysis-summary">
      <h3>AI 解析结果</h3>
      <p>${escapeHtml(analysis?.summary || "已完成基础解析，请检查角色和场景拆分后继续生成剧本。")}</p>
      <ul>
        <li>识别角色：${characters.length} 个</li>
        <li>拆分场景：${scenes.length} 场</li>
        <li>下一步：确认解析结果后点击左侧“生成剧本”</li>
      </ul>
    </section>`;
  charactersPanel.innerHTML = characters.length
    ? table(["角色名", "身份", "性格", "人物目标 / 描述"], characters.map((c) => [c.name, c.role, (c.traits || []).join("、"), c.description || ""]))
    : emptyState();
  scenesPanel.innerHTML = scenes.length
    ? table(["场次", "章节", "地点", "时间", "人物", "冲突 / 作用"], scenes.map((s, i) => [i + 1, s.chapter, s.location, s.time, (s.characters || []).join("、"), s.summary]))
    : emptyState();
  storyboardPanel.innerHTML = `<div class="empty-result"><strong>分镜等待生成</strong><span>点击右上角“生成分镜”，系统会基于场景整理镜号、景别、画面、台词、音效和时长。</span></div>`;
}

function emptyState() {
  return `<div class="empty-result"><strong>请上传要解析的小说</strong><span>上传 TXT/Markdown 文件，或粘贴小说正文后再点击“解析小说”。</span></div>`;
}

function renderPreview(scriptData) {
  if (!scriptData) return emptyState();
  return (scriptData.scenes || []).map((scene, index) => `
    <article class="script-scene">
      <h3>第 ${index + 1} 场　${escapeHtml(scene.location)}　${escapeHtml(scene.time)}</h3>
      <p class="scene-meta">${escapeHtml(scene.title)} · ${escapeHtml(scene.mood || "推进")}</p>
      ${(scene.beats || []).map(renderBeat).join("")}
    </article>`).join("");
}

function renderBeat(beat) {
  if (beat.type === "dialogue") return `<p class="dialogue"><strong>${escapeHtml(beat.character || "角色")}：</strong>${escapeHtml(beat.text)}</p>`;
  return `<p class="beat ${escapeHtml(beat.type)}">${escapeHtml(beat.text)}</p>`;
}

function table(headers, rows) {
  return `<div class="data-table-wrap"><table class="data-table"><thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${escapeHtml(c ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function renderCharacters(scriptData) {
  const characters = scriptData?.characters || [];
  if (!characters.length) return emptyState();
  return table(["角色名", "身份", "性格", "人物目标 / 描述"], characters.map((c) => [c.name, c.role, (c.traits || []).join("、"), c.description || ""]));
}

function renderScenes(scriptData) {
  const scenes = scriptData?.scenes || [];
  if (!scenes.length) return emptyState();
  return table(["场次", "地点", "时间", "人物", "冲突 / 作用"], scenes.map((s, i) => [i + 1, s.location, s.time, (s.characters || []).join("、"), s.summary]));
}

function renderStoryboard(scriptData) {
  const rows = [];
  (scriptData?.scenes || []).forEach((scene, sceneIndex) => {
    (scene.beats || []).forEach((beat, beatIndex) => rows.push([`${sceneIndex + 1}-${beatIndex + 1}`, beat.type === "dialogue" ? "中景" : beat.type === "transition" ? "转场" : "近景", beat.text, beat.type === "dialogue" ? `${beat.character || ""}：${beat.text}` : "", beat.type === "transition" ? "环境声" : "", "3s"]));
  });
  return rows.length ? table(["镜号", "景别", "画面", "台词", "音效", "时长"], rows) : emptyState();
}

function renderAnalysisStoryboard(analysis) {
  const scenes = analysis?.scenes || [];
  const rows = scenes.map((scene, index) => [
    String(index + 1),
    index === 0 ? "远景" : index % 2 === 0 ? "近景" : "中景",
    `${scene.location || "场景"}：${scene.summary || scene.title || "关键剧情推进"}`,
    "",
    scene.mood ? `${scene.mood}氛围` : "环境声",
    "4s",
  ]);
  return rows.length ? table(["镜号", "景别", "画面", "台词", "音效", "时长"], rows) : emptyState();
}

function generateStoryboard() {
  if (!currentScriptData && !currentAnalysis) {
    setStatus("请先解析小说或生成剧本", "is-error");
    return;
  }
  storyboardPanel.innerHTML = currentScriptData ? renderStoryboard(currentScriptData) : renderAnalysisStoryboard(currentAnalysis);
  const title = titleInput.value.trim() || "novel2script";
  const stats = currentScriptData ? parseStats(currentScriptData, currentYaml) : { scenes: currentAnalysis?.scenes?.length || 0, characters: currentAnalysis?.characters?.length || 0, beats: currentAnalysis?.scenes?.length || 0 };
  applyOutputStats(stats);
  maybeSaveHistory({ title, yaml: currentYaml, scriptData: currentScriptData, analysis: currentAnalysis, stats, options: generationOptions(), type: "生成分镜" });
  saveCurrentProject("分镜已生成");
  setProjectStatus("分镜已生成");
  switchTab("storyboard");
  setStatus("分镜已生成", "is-ready");
}

function switchTab(tabName) {
  activeTab = tabName;
  document.querySelectorAll(".result-tabs button").forEach((button) => button.classList.toggle("is-active", button.dataset.tab === tabName));
  const panels = { preview: previewPanel, characters: charactersPanel, scenes: scenesPanel, storyboard: storyboardPanel, yaml: yamlOutput, json: jsonOutput };
  Object.entries(panels).forEach(([name, panel]) => panel.classList.toggle("is-active", name === tabName));
}

function switchView(viewName) {
  activeView = viewName;
  document.querySelectorAll(".top-nav button").forEach((button) => button.classList.toggle("is-active", button.dataset.view === viewName));
  document.querySelectorAll(".view-panel").forEach((panel) => panel.classList.toggle("is-active", panel.dataset.viewPanel === viewName));
  if (viewName === "projects") renderProjects();
  if (viewName === "history") renderHistory();
}

async function copyCurrentView() {
  const activePanel = document.querySelector(".tab-panel.is-active");
  const text = activePanel?.innerText || currentYaml || "";
  setStatus((await copyText(text)) ? "已复制当前视图" : "复制失败，请手动选择文本", "is-ready");
}

async function copyText(text) {
  if (!text.trim()) return false;
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {}
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.top = "-1000px";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    return document.execCommand("copy");
  } finally {
    document.body.removeChild(textarea);
  }
}

function exportMarkdown() {
  if (!currentScriptData && currentAnalysis) {
    const lines = [`# ${titleInput.value.trim() || "小说解析结果"}`, "", "## 故事梗概", currentAnalysis.summary || "", "", "## 角色表"];
    (currentAnalysis.characters || []).forEach((c) => lines.push(`- **${c.name}**：${c.description || c.role}`));
    lines.push("", "## 场景拆分");
    (currentAnalysis.scenes || []).forEach((scene, i) => lines.push(`### 第 ${i + 1} 场 ${scene.location} ${scene.time}`, scene.summary || ""));
    return lines.join("\n");
  }
  if (!currentScriptData) return "# 未生成剧本\n";
  const lines = [`# ${currentScriptData.title}`, "", "## 角色表"];
  (currentScriptData.characters || []).forEach((c) => lines.push(`- **${c.name}**：${c.description || c.role}`));
  lines.push("", "## 分场剧本");
  (currentScriptData.scenes || []).forEach((scene, i) => {
    lines.push(`### 第 ${i + 1} 场 ${scene.location} ${scene.time}`, scene.summary || "");
    (scene.beats || []).forEach((beat) => lines.push(beat.type === "dialogue" ? `${beat.character}：${beat.text}` : beat.text));
  });
  return lines.join("\n");
}

function safeFilename(name) {
  return String(name || "novel2script").replace(/[\\/:*?"<>|]+/g, "_").trim() || "novel2script";
}

function currentViewExport() {
  const title = safeFilename(titleInput.value.trim() || "novel2script");
  const activePanel = document.querySelector(".tab-panel.is-active");
  const panelText = (activePanel?.innerText || "").trim();
  const fallbackMarkdown = exportMarkdown();
  const exporters = {
    preview: { text: panelText || fallbackMarkdown, filename: `${title}-剧本预览.txt` },
    characters: { text: panelText || fallbackMarkdown, filename: `${title}-角色表.txt` },
    scenes: { text: panelText || fallbackMarkdown, filename: `${title}-场景表.txt` },
    storyboard: { text: panelText || fallbackMarkdown, filename: `${title}-分镜表.txt` },
    yaml: { text: currentYaml || yamlOutput.textContent, filename: `${title}.yaml` },
    json: { text: JSON.stringify(currentScriptData || currentAnalysis || {}, null, 2), filename: `${title}.json` },
  };
  return exporters[activeTab] || exporters.preview;
}

function handleExport(format) {
  const title = safeFilename(titleInput.value.trim() || "novel2script");
  if (format === "json") downloadText(JSON.stringify(currentScriptData || currentAnalysis || {}, null, 2), `${title}.json`);
  if (format === "yaml") downloadText(currentYaml || yamlOutput.textContent, `${title}.yaml`);
  if (format === "markdown") downloadText(exportMarkdown(), `${title}.md`);
  if (format === "txt") downloadText((previewPanel.innerText || exportMarkdown()).trim(), `${title}.txt`);
  maybeSaveHistory({ title, yaml: currentYaml, scriptData: currentScriptData, analysis: currentAnalysis, stats: parseStats(currentScriptData, currentYaml), options: generationOptions(), type: "导出记录" });
  setStatus(`已导出 ${format}`, "is-ready");
}

function downloadCurrentView() {
  const exportData = currentViewExport();
  if (!exportData.text.trim()) {
    setStatus("当前视图没有可下载内容", "is-error");
    return;
  }
  downloadText(exportData.text, exportData.filename);
  setStatus(`已下载 ${exportData.filename}`, "is-ready");
}

function downloadText(text, filename) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function readHistory() { return readStore(HISTORY_KEY, []); }
function writeHistory(items) { writeStore(HISTORY_KEY, items.slice(0, MAX_HISTORY_ITEMS)); }
function maybeSaveHistory(entry) {
  if (readSettings().autoSaveHistory === "off") return;
  const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const items = readHistory();
  const record = { id, createdAt: new Date().toISOString(), ...entry };
  writeHistory([record, ...items]);
  persistHistoryToDatabase(record);
  renderHistory();
}

function renderHistory() {
  const items = readHistory().filter((item) => activeHistoryFilter === "全部" || item.type === activeHistoryFilter);
  historyCount.textContent = items.length ? `${items.length} 条记录` : "暂无记录";
  clearHistoryButton.disabled = readHistory().length === 0;
  historyList.innerHTML = items.length ? items.map(historyCard).join("") : `<div class="history-empty">生成后的剧本会自动保存在这里。</div>`;
}

function historyCard(item) {
  const stats = item.stats || {};
  const time = new Date(item.createdAt).toLocaleString("zh-CN", { hour12: false, month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  return `<article class="history-item" data-id="${escapeHtml(item.id)}"><div class="history-main"><strong>${escapeHtml(item.title || "未命名剧本")}</strong><span>${escapeHtml(item.type || "剧本生成")} · ${stats.scenes || 0} 场 · ${time}</span></div><div class="history-actions"><button data-action="restore" title="查看">↩</button><button data-action="copy" title="复制">⧉</button><button data-action="download" title="导出">⇩</button><button data-action="delete" title="删除">×</button></div></article>`;
}

async function handleHistoryAction(event) {
  const button = event.target.closest("button[data-action]");
  const node = event.target.closest(".history-item");
  if (!button || !node) return;
  const items = readHistory();
  const item = items.find((entry) => entry.id === node.dataset.id);
  if (!item) return;
  if (button.dataset.action === "restore") restoreHistoryItem(item);
  if (button.dataset.action === "copy") setStatus((await copyText(item.yaml || "")) ? "已复制历史 YAML" : "复制失败", "is-ready");
  if (button.dataset.action === "download") downloadText(item.yaml || JSON.stringify(item.scriptData || item.analysis || {}, null, 2), `${safeFilename(item.title || "novel2script")}.yaml`);
  if (button.dataset.action === "delete") {
    writeHistory(items.filter((entry) => entry.id !== item.id));
    renderHistory();
    setStatus("已删除历史记录", "is-ready");
  }
}

function restoreHistoryItem(item) {
  currentYaml = item.yaml || "";
  currentScriptData = item.scriptData || null;
  currentAnalysis = item.analysis || null;
  titleInput.value = item.title || titleInput.value;
  if (currentScriptData) renderResult(currentScriptData, currentYaml);
  else if (currentAnalysis) renderAnalysisResult(currentAnalysis);
  else renderResult(null, currentYaml);
  applyOutputStats(item.stats || parseStats(currentScriptData, currentYaml));
  setProjectStatus(item.type === "解析小说" ? "已解析" : item.type === "剧本生成" ? "剧本已生成" : "草稿");
  switchTab("preview");
  switchView("workbench");
  setStatus("已恢复历史记录", "is-ready");
}

function readProjects() { return readStore(PROJECTS_KEY, []); }
function writeProjects(items) { writeStore(PROJECTS_KEY, items); }
function saveCurrentProject(status = "草稿") {
  const title = titleInput.value.trim() || "未命名项目";
  const projects = readProjects();
  const existing = projects.find((project) => project.title === title);
  const project = {
    id: existing?.id || `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    title,
    source_text: novelInput.value,
    status,
    updated_at: new Date().toISOString(),
    created_at: existing?.created_at || new Date().toISOString(),
    yaml: currentYaml,
    scriptData: currentScriptData,
    analysis: currentAnalysis,
    stats: parseStats(currentScriptData, currentYaml),
  };
  writeProjects([project, ...projects.filter((item) => item.id !== project.id)]);
  persistProjectToDatabase(project);
  currentProjectStatus = status;
  updateWorkspaceMeta();
  renderProjects();
}

function renderProjects() {
  const query = projectSearch.value.trim().toLowerCase();
  const projects = readProjects().filter((project) => !query || project.title.toLowerCase().includes(query));
  projectCount.textContent = projects.length ? `${projects.length} 个项目` : "暂无项目";
  projectList.innerHTML = projects.length ? projects.map(projectCard).join("") : `<div class="history-empty">保存当前输入后，项目会出现在这里。</div>`;
}

function projectCard(project) {
  const stats = project.stats || {};
  const updated = new Date(project.updated_at).toLocaleString("zh-CN", { hour12: false });
  return `<article class="project-card" data-id="${escapeHtml(project.id)}"><h3>《${escapeHtml(project.title)}》</h3><p>状态：${escapeHtml(project.status)}</p><p>字数：${(project.source_text || "").replace(/\s/g, "").length} · 场景：${stats.scenes || 0} · 角色：${stats.characters || 0}</p><p>最近编辑：${updated}</p><div class="card-actions"><button data-project-action="open">继续编辑</button><button data-project-action="export">导出</button><button data-project-action="copy">复制</button><button data-project-action="delete">删除</button></div></article>`;
}

async function handleProjectAction(event) {
  const button = event.target.closest("button[data-project-action]");
  const node = event.target.closest(".project-card");
  if (!button || !node) return;
  const projects = readProjects();
  const project = projects.find((item) => item.id === node.dataset.id);
  if (!project) return;
  if (button.dataset.projectAction === "open") {
    titleInput.value = project.title;
    novelInput.value = project.source_text || "";
    currentYaml = project.yaml || "";
    currentScriptData = project.scriptData || null;
    currentAnalysis = project.analysis || null;
    if (currentScriptData) renderResult(currentScriptData, currentYaml);
    else if (currentAnalysis) renderAnalysisResult(currentAnalysis);
    else renderResult(null, currentYaml);
    applyOutputStats(project.stats || parseStats(currentScriptData, currentYaml));
    setProjectStatus(project.status || "草稿");
    updateInputMetrics();
    switchView("workbench");
  }
  if (button.dataset.projectAction === "export") downloadText(project.yaml || JSON.stringify(project.scriptData || project.analysis || {}, null, 2), `${safeFilename(project.title || "novel2script")}.yaml`);
  if (button.dataset.projectAction === "copy") await copyText(project.yaml || project.source_text || "");
  if (button.dataset.projectAction === "delete") {
    writeProjects(projects.filter((item) => item.id !== project.id));
    deleteProjectFromDatabase(project.id);
    renderProjects();
  }
}

function readSettings() {
  return {
    provider: "DeepSeek",
    modelName: "deepseek-chat",
    apiKey: "************",
    temperature: "0.7",
    maxTokens: "4000",
    autoSaveHistory: "on",
    ...readStore(SETTINGS_KEY, {}),
  };
}

function applySettings() {
  const settings = readSettings();
  $("#providerSelect").value = settings.provider;
  $("#modelNameInput").value = settings.modelName;
  $("#apiKeyInput").value = settings.apiKey;
  $("#temperatureInput").value = settings.temperature;
  $("#maxTokensInput").value = settings.maxTokens;
  $("#autoSaveHistory").value = settings.autoSaveHistory;
}

function saveSettings() {
  const settings = {
    provider: $("#providerSelect").value,
    modelName: $("#modelNameInput").value,
    apiKey: $("#apiKeyInput").value.replace(/.(?=.{4})/g, "*"),
    temperature: $("#temperatureInput").value,
    maxTokens: $("#maxTokensInput").value,
    autoSaveHistory: $("#autoSaveHistory").value,
  };
  writeStore(SETTINGS_KEY, settings);
  persistSettingsToDatabase(settings);
  applySettings();
  updateWorkspaceMeta();
  setStatus("设置已保存", "is-ready");
}

function resetSettings() {
  localStorage.removeItem(SETTINGS_KEY);
  applySettings();
  updateWorkspaceMeta();
  setStatus("已恢复默认设置", "is-ready");
}

function resetOutput() {
  currentYaml = "";
  currentScriptData = null;
  currentAnalysis = null;
  renderResult(null, "");
  applyOutputStats({ scenes: 0, characters: 0, beats: 0 });
}

function initializeEmptyState() {
  titleInput.value = "";
  novelInput.value = "";
  resetOutput();
  setProjectStatus("待上传");
  updateInputMetrics();
  setStatus("上传或粘贴要解析的小说");
}

function clearAll() {
  titleInput.value = "";
  novelInput.value = "";
  resetOutput();
  setProjectStatus("草稿");
  updateInputMetrics();
  setStatus("上传或粘贴要解析的小说");
}

function fillSample() {
  titleInput.value = "夜色旧宅";
  novelInput.value = sampleText;
  resetOutput();
  setProjectStatus("待解析");
  updateInputMetrics();
  setStatus("短篇示例已填入", "is-ready");
}

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

form.addEventListener("submit", convertNovel);
document.querySelectorAll(".top-nav button").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)));
document.querySelectorAll(".result-tabs button").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.tab)));
document.querySelectorAll("[data-export-format]").forEach((button) => button.addEventListener("click", () => handleExport(button.dataset.exportFormat)));
document.querySelectorAll("[data-history-filter]").forEach((button) => button.addEventListener("click", () => { activeHistoryFilter = button.dataset.historyFilter; document.querySelectorAll("[data-history-filter]").forEach((item) => item.classList.toggle("is-active", item === button)); renderHistory(); }));
novelInput.addEventListener("input", updateInputMetrics);
titleInput.addEventListener("input", updateInputMetrics);
analyzeButton.addEventListener("click", analyzeNovel);
importButton.addEventListener("click", () => novelFileInput.click());
importInlineButton.addEventListener("click", () => novelFileInput.click());
importProjectButton.addEventListener("click", () => novelFileInput.click());
novelFileInput.addEventListener("change", async () => { await importNovelFile(novelFileInput.files?.[0]); novelFileInput.value = ""; });
sampleButton.addEventListener("click", fillSample);
clearButton.addEventListener("click", clearAll);
copyButton.addEventListener("click", copyCurrentView);
storyboardButton.addEventListener("click", generateStoryboard);
downloadButton.addEventListener("click", downloadCurrentView);
saveProjectButton.addEventListener("click", () => { saveCurrentProject("草稿"); setStatus("项目已保存", "is-ready"); });
newProjectButton.addEventListener("click", () => { clearAll(); switchView("workbench"); });
projectSearch.addEventListener("input", renderProjects);
projectList.addEventListener("click", handleProjectAction);
clearHistoryButton.addEventListener("click", () => { writeHistory([]); renderHistory(); setStatus("历史已清空", "is-ready"); });
historyList.addEventListener("click", handleHistoryAction);
$("#saveSettingsButton").addEventListener("click", saveSettings);
$("#resetSettingsButton").addEventListener("click", resetSettings);
novelInput.addEventListener("dragover", (event) => { event.preventDefault(); novelInput.classList.add("drop-ready"); });
novelInput.addEventListener("dragleave", () => novelInput.classList.remove("drop-ready"));
novelInput.addEventListener("drop", async (event) => { event.preventDefault(); novelInput.classList.remove("drop-ready"); await importNovelFile(event.dataTransfer?.files?.[0]); });

applySettings();
initializeEmptyState();
renderProjects();
renderHistory();
switchTab("preview");
loadLlmStatus();
loadDatabaseState().then(() => {
  renderProjects();
  renderHistory();
});
