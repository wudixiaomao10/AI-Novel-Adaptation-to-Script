# Novel2Script：AI 小说转剧本工具

Novel2Script 是一个基于 FastAPI 的 AI 小说转剧本网页应用。用户可以输入或上传小说文本，系统会自动完成小说解析、角色识别、场景拆分、剧本生成、分镜生成和结果导出。

项目采用“AI 负责语义理解，代码负责结构化和持久化”的设计思路，适合作为 AI 应用课程项目、简历项目或小说改编工具原型。

## 核心功能

- 小说标题与正文输入
- TXT / Markdown 小说文件上传
- AI 解析小说，生成故事梗概、角色表和场景表
- 生成标准剧本，包括场次、动作、对白和场景摘要
- 生成分镜表，包括镜号、景别、画面、台词、音效和时长
- 多视图预览：剧本预览、角色表、场景表、分镜表、YAML、JSON
- 项目管理：保存、打开、删除、继续编辑
- 历史记录：记录解析、生成剧本、生成分镜和导出操作
- 导出 Markdown、TXT、JSON、YAML
- SQLite 数据库存储项目、历史记录和设置
- 支持增强 Mock，也支持切换真实 LLM

## 技术栈

- 后端：Python、FastAPI、Pydantic
- 前端：HTML、CSS、JavaScript
- 数据库：SQLite
- 结构化输出：JSON、YAML
- LLM：DeepSeek / OpenAI-compatible / Qwen / Mock

## 项目结构

```text
.
├── README.md
└── backend
    ├── main.py
    ├── requirements.txt
    ├── .env.example
    ├── schemas
    │   └── script_schema.py
    ├── services
    │   ├── beat_writer.py
    │   ├── chapter_parser.py
    │   ├── config.py
    │   ├── database.py
    │   ├── extractor.py
    │   ├── llm_client.py
    │   ├── prompt_builder.py
    │   ├── scene_planner.py
    │   ├── transformer.py
    │   ├── validator.py
    │   └── yaml_exporter.py
    └── static
        ├── index.html
        ├── styles.css
        └── app.js
```

## 运行方式

进入后端目录：

```powershell
cd backend
```

安装依赖：

```powershell
pip install -r requirements.txt
```

启动服务：

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

打开浏览器访问：

```text
http://127.0.0.1:8001/
```

## LLM 配置

项目默认支持增强 Mock 生成，不配置真实模型也可以运行。

如果需要接入真实 LLM，可以复制环境变量示例：

```powershell
copy .env.example .env
```

然后在 `backend/.env` 中配置：

```env
NOVEL2SCRIPT_LLM_PROVIDER=deepseek
NOVEL2SCRIPT_LLM_MODEL=deepseek-chat
NOVEL2SCRIPT_LLM_API_KEY=your_api_key
NOVEL2SCRIPT_LLM_BASE_URL=https://api.deepseek.com
NOVEL2SCRIPT_USE_REAL_LLM=true
```

修改 `.env` 后需要重启服务。

## 数据库

项目使用 SQLite 作为数据库。服务启动后会自动创建数据库文件：

```text
backend/data/novel2script.db
```

数据库包含：

```text
projects          项目表
scripts           剧本结果表
storyboards       分镜表
history_records   历史记录表
settings          设置表
```

`backend/data/` 已加入 `.gitignore`，数据库文件不会提交到仓库。

## 主要接口

```text
GET    /api/health
POST   /api/novel/parse
POST   /api/convert

GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}
DELETE /api/projects/{id}

GET    /api/history
POST   /api/history

GET    /api/settings
PUT    /api/settings

POST   /api/export/yaml
```

## 使用流程

```text
输入小说或上传文件
        ↓
点击“解析小说”
        ↓
查看故事梗概、角色表、场景表
        ↓
点击“生成剧本”
        ↓
查看剧本预览和结构化结果
        ↓
点击“生成分镜”
        ↓
导出 Markdown / TXT / JSON / YAML
```

## 项目亮点

传统做法通常直接让大模型一次性输出完整 YAML 或剧本，容易出现格式错误、字段缺失和剧情压缩严重的问题。

Novel2Script 采用分阶段生成方式：

```text
小说解析 -> 角色提取 -> 场景拆分 -> 剧本生成 -> 分镜生成 -> 数据库存储 -> 导出
```

这种设计降低了模型输出不稳定带来的影响，也让项目更接近真实 AI 应用的工程结构。
