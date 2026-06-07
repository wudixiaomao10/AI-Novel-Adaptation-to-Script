# Novel2Script

FastAPI web app for converting novel text into an editable YAML script draft.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

The root page is a web workspace with short-story or chaptered novel input, one-click TXT/Markdown import, drag-and-drop import, YAML output, copy, download, and live text statistics.

## LLM Mode

By default, Novel2Script uses an enhanced mock pipeline:

```text
extract_story_facts -> plan_scenes -> write_scene_beats -> validate -> YAML
```

When a real LLM is enabled, Novel2Script uses a staged pipeline instead of one-shot YAML generation:

```text
outline_json -> scene_beats_json -> code_assembly -> Pydantic validation -> YAML
```

The model only returns JSON. Python assembles and validates the final Script object, then `yaml.dump()` exports the final YAML.

To switch to a real OpenAI-compatible LLM, set environment variables before starting Uvicorn:

```bash
copy .env.example .env
set NOVEL2SCRIPT_LLM_PROVIDER=openai_compatible
set NOVEL2SCRIPT_LLM_API_KEY=your_api_key
set NOVEL2SCRIPT_LLM_BASE_URL=https://api.openai.com/v1
set NOVEL2SCRIPT_LLM_MODEL=your_model_name
uvicorn main:app --reload
```

On Windows PowerShell you can also edit `backend/.env` directly:

```text
NOVEL2SCRIPT_LLM_PROVIDER=deepseek
NOVEL2SCRIPT_LLM_API_KEY=your_api_key
NOVEL2SCRIPT_LLM_MODEL=deepseek-chat
```

The app reads `backend/.env` at startup. Restart Uvicorn after changing it.

Supported provider values:

```text
mock
openai
openai_compatible
deepseek
qwen
```

## API

### GET /api/health

Response:

```json
{
  "status": "ok",
  "service": "Novel2Script",
  "llm_provider": "mock",
  "real_llm_enabled": false
}
```

### POST /api/convert

Request:

```json
{
  "title": "夜色旧宅",
  "novel_text": "第一章 初遇\n林夏推开旧宅大门，发现屋里一片漆黑。\n\n第二章 暗流\n楼上传来脚步声，林夏握紧手电筒。\n\n第三章 真相\n沈砚从阴影中走出，说出了旧宅的秘密。"
}
```

Response:

```json
{
  "success": true,
  "script_yaml": "script:\n  title: 夜色旧宅\n  ..."
}
```

### POST /api/export/yaml

Request:

```json
{
  "filename": "夜色旧宅.yaml",
  "script_yaml": "script:\n  title: 夜色旧宅\n"
}
```

Response: downloadable YAML file.

## curl Example

```bash
curl -X POST "http://127.0.0.1:8000/api/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "夜色旧宅",
    "novel_text": "第一章 初遇\n林夏推开旧宅大门，发现屋里一片漆黑。\n\n第二章 暗流\n楼上传来脚步声，林夏握紧手电筒。\n\n第三章 真相\n沈砚从阴影中走出，说出了旧宅的秘密。"
  }'
```
