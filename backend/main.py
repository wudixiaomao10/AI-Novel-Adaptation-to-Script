from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from schemas.script_schema import ScriptResponse
from services.chapter_parser import split_chapters, validate_min_chapters
from services.config import load_environment
from services.database import (
    delete_project,
    get_project,
    init_database,
    list_history,
    list_projects,
    read_settings,
    save_history,
    save_project,
    upsert_setting,
)
from services.extractor import extract_story_facts
from services.scene_planner import plan_scenes
from services.transformer import NovelTransformer
from services.yaml_exporter import export_script_to_yaml


app = FastAPI(title="Novel2Script API", version="0.1")
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
load_environment(BASE_DIR / ".env")
transformer = NovelTransformer()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup() -> None:
    """Initialize SQLite storage."""
    init_database()


class ConvertRequest(BaseModel):
    """Request body for novel to script conversion."""

    title: str = Field(min_length=1)
    novel_text: str = Field(min_length=1)
    script_type: str = "影视剧本"
    style: str = "悬疑"
    output_language: str = "中文"
    episodes: int = Field(default=1, ge=1, le=100)
    episode_duration: str = "3 分钟"
    dialogue_density: str = "中"
    adaptation_level: str = "适度改编"
    ending_type: str = "悬念式"

    def generation_options(self) -> dict[str, Any]:
        """Return user-selected generation options."""
        return {
            "script_type": self.script_type,
            "style": self.style,
            "output_language": self.output_language,
            "episodes": self.episodes,
            "episode_duration": self.episode_duration,
            "dialogue_density": self.dialogue_density,
            "adaptation_level": self.adaptation_level,
            "ending_type": self.ending_type,
        }


class ParseNovelRequest(BaseModel):
    """Request body for novel content analysis."""

    title: str = Field(min_length=1)
    novel_text: str = Field(min_length=1)


class ExportYamlRequest(BaseModel):
    """Request body for downloading generated YAML."""

    filename: str = "novel2script.yaml"
    script_yaml: str = Field(min_length=1)


class ProjectPayload(BaseModel):
    """Project persistence payload."""

    id: str | None = None
    title: str = Field(min_length=1)
    source_text: str = ""
    status: str = "草稿"
    yaml: str = ""
    scriptData: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    stats: dict[str, Any] | None = None
    created_at: str | None = None


class HistoryPayload(BaseModel):
    """History persistence payload."""

    id: str | None = None
    title: str = Field(min_length=1)
    type: str = "操作"
    status: str = "成功"
    createdAt: str | None = None
    yaml: str = ""
    scriptData: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    stats: dict[str, Any] | None = None
    options: dict[str, Any] | None = None


class SettingsPayload(BaseModel):
    """Settings persistence payload."""

    settings: dict[str, Any]


@app.get("/")
async def read_root() -> FileResponse:
    """Serve the Novel2Script web application."""
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/convert", response_model=ScriptResponse)
async def convert_novel(request: ConvertRequest) -> ScriptResponse:
    """Convert novel text into an editable YAML script draft."""
    try:
        chapters = split_chapters(request.novel_text)
        validate_min_chapters(chapters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        script = await transformer.convert(
            title=request.title,
            chapters=chapters,
            generation_options=request.generation_options(),
        )
        script.metadata["generation_options"] = request.generation_options()
        script_yaml = export_script_to_yaml(script)
        script_data = script.model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal server error") from exc

    return ScriptResponse(success=True, script_yaml=script_yaml, script_data=script_data)


@app.post("/api/novel/parse")
async def parse_novel(request: ParseNovelRequest) -> dict[str, Any]:
    """Parse novel text into summary, characters, and scene outline."""
    try:
        chapters = split_chapters(request.novel_text)
        validate_min_chapters(chapters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    facts = extract_story_facts(title=request.title, chapters=chapters)
    scenes = plan_scenes(facts=facts, chapters=chapters)
    summary = " ".join(
        str(chapter_fact.get("summary") or "")
        for chapter_fact in facts.get("chapter_facts", [])
    ).strip()
    payload = {
        "summary": summary,
        "characters": facts["characters"],
        "scenes": [
            {
                "id": scene["id"],
                "chapter": scene["chapter"],
                "title": scene["title"],
                "location": scene["location"],
                "time": scene["time"],
                "mood": scene["mood"],
                "summary": scene["summary"],
                "characters": scene["characters"],
            }
            for scene in scenes
        ],
    }
    payload["structure_yaml"] = yaml.dump(payload, allow_unicode=True, sort_keys=False)
    return payload


@app.get("/api/projects")
async def api_list_projects() -> dict[str, Any]:
    """List saved projects from SQLite."""
    return {"projects": list_projects()}


@app.post("/api/projects")
async def api_save_project(payload: ProjectPayload) -> dict[str, Any]:
    """Create or update one project in SQLite."""
    return {"project": save_project(payload.model_dump())}


@app.get("/api/projects/{project_id}")
async def api_get_project(project_id: str) -> dict[str, Any]:
    """Load one project from SQLite."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@app.delete("/api/projects/{project_id}")
async def api_delete_project(project_id: str) -> dict[str, Any]:
    """Delete one project from SQLite."""
    if not delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}


@app.get("/api/history")
async def api_list_history() -> dict[str, Any]:
    """List saved history records from SQLite."""
    return {"history": list_history()}


@app.post("/api/history")
async def api_save_history(payload: HistoryPayload) -> dict[str, Any]:
    """Save one history record in SQLite."""
    return {"record": save_history(payload.model_dump())}


@app.get("/api/settings")
async def api_get_settings() -> dict[str, Any]:
    """Load persisted settings."""
    return {"settings": read_settings()}


@app.put("/api/settings")
async def api_save_settings(payload: SettingsPayload) -> dict[str, Any]:
    """Persist settings values."""
    for key, value in payload.settings.items():
        upsert_setting(key, value)
    return {"settings": read_settings()}


@app.post("/api/export/yaml")
async def export_yaml(request: ExportYamlRequest) -> Response:
    """Return YAML content as a downloadable file."""
    safe_filename = Path(request.filename).name or "novel2script.yaml"
    if not safe_filename.endswith((".yaml", ".yml")):
        safe_filename = f"{safe_filename}.yaml"

    return Response(
        content=request.script_yaml,
        media_type="application/x-yaml",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    """Return lightweight API health data."""
    llm_status = transformer.llm_client.status()
    return {
        "status": "ok",
        "service": "Novel2Script",
        "llm_provider": llm_status["provider"],
        "real_llm_enabled": llm_status["enabled"],
        "llm_configured": llm_status["configured"],
        "database": str(BASE_DIR / "data" / "novel2script.db"),
    }


@app.get("/api/llm/status")
async def llm_status() -> dict[str, Any]:
    """Return safe LLM configuration status."""
    return transformer.llm_client.status()
