# Novel2Script 项目总结

Novel2Script 是一个 AI 小说转剧本网页应用，目标是把小说内容转换为故事梗概、角色表、场景表、剧本预览、分镜表以及 YAML / JSON 结构化结果。项目采用精简工作流：小说输入 -> AI 解析 -> 剧本生成 -> 分镜生成 -> 导出。

## 一、项目定位

Novel2Script 面向小说作者、短剧创作者、课程项目展示和 AI 应用开发学习者。它不是简单的文本生成页面，而是一个具备完整创作流程的 AI 工具。

系统默认生成中文标准剧本，并自动完成角色识别、场景拆分、剧本结构化和分镜整理。

## 二、技术结构

后端使用 Python + FastAPI。

前端使用原生 HTML、CSS、JavaScript。

数据支持 SQLite 后端持久化，同时前端保留浏览器 localStorage 作为本地缓存。项目记录、历史记录和设置项都会同步写入后端数据库。

LLM 支持增强 Mock，也支持真实 LLM。当前项目已支持通过环境变量接入 DeepSeek。

## 三、项目目录

```text
backend/
├── main.py                 FastAPI 入口
├── requirements.txt        Python 依赖
├── .env.example            环境变量示例
├── schemas/
│   └── script_schema.py    剧本数据结构
├── services/
│   ├── chapter_parser.py   小说章节/短篇解析
│   ├── database.py         SQLite 数据库持久化
│   ├── extractor.py        角色和故事信息提取
│   ├── scene_planner.py    场景拆分
│   ├── beat_writer.py      动作/对白生成
│   ├── transformer.py      小说转剧本主流程
│   ├── llm_client.py       真实 LLM 调用
│   └── yaml_exporter.py    YAML 导出
└── static/
    ├── index.html          页面结构
    ├── styles.css          页面样式
    └── app.js              前端交互逻辑
```

## 四、如何运行

进入项目后端目录：

```powershell
cd E:\AI小说\backend
```

安装依赖：

```powershell
pip install -r requirements.txt
```

启动服务：

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

浏览器打开：

```text
http://127.0.0.1:8001/
```

## 五、真实 LLM 配置

如果要使用真实 LLM，需要在 `backend/.env` 中配置：

```env
NOVEL2SCRIPT_LLM_PROVIDER=deepseek
NOVEL2SCRIPT_LLM_MODEL=deepseek-chat
NOVEL2SCRIPT_LLM_API_KEY=你的 API Key
NOVEL2SCRIPT_LLM_BASE_URL=https://api.deepseek.com
NOVEL2SCRIPT_USE_REAL_LLM=true
```

如果不配置真实 LLM，系统会使用增强 Mock 流程，仍然可以完成小说解析和基础剧本生成。

## 六、主要功能

### 1. 小说输入

支持输入小说标题和正文，也支持上传 TXT / Markdown 小说文件。

### 2. AI 解析小说

点击“解析小说”后，系统会生成：

- 故事梗概
- 主要角色
- 角色描述
- 场景拆分
- 场景地点、时间、氛围和摘要

### 3. 剧本生成

点击“生成剧本”后，系统会把小说转换为标准剧本结构，包括：

- 场次
- 地点
- 时间
- 动作描写
- 人物对白
- 场景摘要

### 4. 分镜生成

根据解析结果或剧本内容生成分镜表，包括：

- 镜号
- 景别
- 画面
- 台词
- 音效
- 时长

### 5. 多视图预览

右侧结果区支持多个 Tab：

- 剧本预览
- 角色表
- 场景表
- 分镜表
- YAML
- JSON

### 6. 项目管理

支持保存项目、打开项目、继续编辑、删除项目、导出项目。

### 7. 历史记录

系统会记录关键操作：

- 解析小说
- 剧本生成
- 生成分镜
- 导出记录

### 8. 导出功能

支持导出：

- Markdown
- TXT
- JSON
- YAML

### 9. 模型设置

设置页保留模型相关配置：

- Provider
- 模型名称
- API Key
- temperature
- max_tokens

### 10. 数据库持久化

项目已接入 SQLite 数据库，数据库文件运行后自动创建：

```text
backend/data/novel2script.db
```

当前包含 5 张表：

```text
projects          项目表
scripts           剧本结果表
storyboards       分镜表
history_records   历史记录表
settings          设置表
```

对应后端接口包括：

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}
DELETE /api/projects/{id}
GET    /api/history
POST   /api/history
GET    /api/settings
PUT    /api/settings
```

## 七、项目亮点

Novel2Script 采用分阶段生成思路，而不是让大模型一次性完成所有工作。系统先解析小说，再拆分场景，最后生成剧本和结构化结果。这种方式能降低长文本生成时的格式错误，也更符合真实 AI 应用的工程流程。

项目体现了“AI 负责语义理解，代码负责结构校验和格式输出”的工程原则。

## 八、当前完成度

当前版本已经具备一个完整 AI 应用的基本能力：

- 有前端页面
- 有后端 API
- 有真实 LLM 接入
- 有增强 Mock 兜底
- 有结构化数据
- 有剧本预览
- 有分镜表
- 有导出能力
- 有项目管理
- 有历史记录
- 有 SQLite 数据库持久化

整体上，Novel2Script 已经可以作为课程展示、简历项目或继续扩展为专业剧本创作平台的基础版本。
