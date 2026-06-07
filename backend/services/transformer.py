from typing import Any, Dict, List

from schemas.script_schema import Script
from services.beat_writer import write_scene_beats
from services.extractor import extract_story_facts
from services.llm_client import LLMClient
from services.prompt_builder import build_outline_prompt, build_scene_beats_prompt
from services.scene_planner import plan_scenes
from services.validator import validate_script_data


Chapter = Dict[str, str | int]


class NovelTransformer:
    """Convert parsed novel chapters into a validated script structure."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    async def convert(
        self,
        title: str,
        chapters: List[Chapter],
        generation_options: Dict[str, Any] | None = None,
    ) -> Script:
        """Convert chapters into a Script Pydantic object."""
        raw_script = await self._call_llm(
            title=title,
            chapters=chapters,
            generation_options=generation_options or {},
        )
        return validate_script_data(raw_script)

    async def _call_llm(
        self,
        title: str,
        chapters: List[Chapter],
        generation_options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Use real multi-stage LLM generation when configured, otherwise mock."""
        if self.llm_client.is_enabled:
            return await self._real_llm_generate(
                title=title,
                chapters=chapters,
                generation_options=generation_options,
            )

        return self._mock_generate(
            title=title,
            chapters=chapters,
            generation_options=generation_options,
        )

    async def _real_llm_generate(
        self,
        title: str,
        chapters: List[Chapter],
        generation_options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate script data through outline, per-scene beats, and code assembly."""
        outline_prompt = build_outline_prompt(
            title=title,
            chapters=chapters,
            generation_options=generation_options,
        )
        outline_data = await self.llm_client.complete_json(outline_prompt)

        characters = self._normalize_characters(outline_data)
        scene_outlines = self._normalize_scene_outlines(outline_data, chapters)
        scenes: List[Dict[str, Any]] = []

        for index, outline in enumerate(scene_outlines, start=1):
            source_text = self._source_text_for_scene(outline, chapters)
            beats_prompt = build_scene_beats_prompt(
                title=title,
                characters=characters,
                scene_outline=outline,
                source_text=source_text,
                generation_options=generation_options,
            )
            beats_data = await self.llm_client.complete_json(beats_prompt)
            scenes.append(
                {
                    "id": str(outline.get("id") or f"scene_{index:03d}"),
                    "chapter": int(outline.get("chapter") or 1),
                    "title": str(outline.get("title") or f"场景 {index}"),
                    "location": str(outline.get("location") or "未知地点"),
                    "time": str(outline.get("time") or "未知时间"),
                    "mood": outline.get("mood") or "推进",
                    "summary": str(outline.get("summary") or "本场戏承接原文关键情节。"),
                    "characters": self._scene_characters(outline, characters),
                    "beats": self._normalize_beats(beats_data),
                }
            )

        return {
            "title": title,
            "source_type": "novel",
            "version": "0.1",
            "language": "zh-CN",
            "metadata": {
                "source_chapter_count": len(chapters),
                "generated_by": "real_llm",
                "pipeline": ["outline_json", "scene_beats_json", "code_assembly"],
                "llm_provider": self.llm_client.settings.provider,
                "llm_model": self.llm_client.settings.model,
                "generation_options": generation_options,
            },
            "characters": characters,
            "scenes": scenes,
        }

    def _mock_generate(
        self,
        title: str,
        chapters: List[Chapter],
        generation_options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate structured script data through extract-plan-write mock steps."""
        facts = extract_story_facts(title=title, chapters=chapters)
        scene_plans = plan_scenes(facts=facts, chapters=chapters)
        scenes = []

        for plan in scene_plans:
            scenes.append(
                {
                    "id": plan["id"],
                    "chapter": plan["chapter"],
                    "title": plan["title"],
                    "location": plan["location"],
                    "time": plan["time"],
                    "mood": plan["mood"],
                    "summary": plan["summary"],
                    "characters": plan["characters"],
                    "beats": write_scene_beats(plan),
                }
            )

        return {
            "title": title,
            "source_type": "novel",
            "version": "0.1",
            "language": "zh-CN",
            "metadata": {
                "source_chapter_count": len(chapters),
                "generated_by": "enhanced_mock",
                "pipeline": ["extract_story_facts", "plan_scenes", "write_scene_beats"],
                "generation_options": generation_options,
            },
            "characters": facts["characters"],
            "scenes": scenes,
        }

    def _normalize_characters(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        characters = data.get("characters") or data.get("character_table") or []
        normalized = []

        for index, character in enumerate(characters, start=1):
            if not isinstance(character, dict):
                continue
            normalized.append(
                {
                    "id": str(character.get("id") or f"char_{index:03d}"),
                    "name": str(character.get("name") or f"角色{index}"),
                    "role": str(character.get("role") or ("protagonist" if index == 1 else "supporting")),
                    "description": character.get("description") or "根据原文提取的剧本角色。",
                    "traits": character.get("traits") if isinstance(character.get("traits"), list) else [],
                }
            )

        if not normalized:
            normalized.append(
                {
                    "id": "char_001",
                    "name": "主角",
                    "role": "protagonist",
                    "description": "根据原文提取的剧本主角。",
                    "traits": ["坚韧"],
                }
            )

        return normalized

    def _normalize_scene_outlines(
        self,
        data: Dict[str, Any],
        chapters: List[Chapter],
    ) -> List[Dict[str, Any]]:
        outlines = data.get("scenes") or data.get("scene_outline") or data.get("scene_outlines") or []
        normalized = []

        for index, outline in enumerate(outlines, start=1):
            if not isinstance(outline, dict):
                continue
            normalized.append(
                {
                    "id": str(outline.get("id") or f"scene_{index:03d}"),
                    "chapter": int(outline.get("chapter") or 1),
                    "title": str(outline.get("title") or f"场景 {index}"),
                    "location": str(outline.get("location") or "未知地点"),
                    "time": str(outline.get("time") or "未知时间"),
                    "mood": outline.get("mood") or "推进",
                    "summary": str(outline.get("summary") or "本场戏承接原文关键情节。"),
                    "characters": outline.get("characters") if isinstance(outline.get("characters"), list) else [],
                }
            )

        if normalized:
            return normalized

        facts = extract_story_facts(title="未命名剧本", chapters=chapters)
        return plan_scenes(facts=facts, chapters=chapters)

    def _normalize_beats(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        beats = data.get("beats") or data.get("scene", {}).get("beats") or []
        normalized = []

        for beat in beats:
            if not isinstance(beat, dict):
                continue
            beat_type = beat.get("type") if beat.get("type") in {"action", "dialogue", "narration", "transition"} else "action"
            character = beat.get("character")
            if beat_type == "dialogue" and not character:
                character = "主角"
            normalized.append(
                {
                    "type": beat_type,
                    "text": str(beat.get("text") or "场景动作继续推进。"),
                    "character": character,
                    "emotion": beat.get("emotion"),
                }
            )

        if normalized:
            return normalized

        return [
            {"type": "action", "text": "人物在场景中展开关键行动。", "character": None, "emotion": None},
            {"type": "dialogue", "text": "我们必须继续。", "character": "主角", "emotion": "克制"},
            {"type": "narration", "text": "局势持续变化，冲突进一步加深。", "character": None, "emotion": None},
        ]

    def _source_text_for_scene(self, outline: Dict[str, Any], chapters: List[Chapter]) -> str:
        chapter_number = int(outline.get("chapter") or 1)
        for chapter in chapters:
            if int(chapter.get("chapter_index") or 1) == chapter_number:
                return str(chapter.get("content") or "")
        return str(chapters[0].get("content") or "") if chapters else ""

    def _scene_characters(self, outline: Dict[str, Any], characters: List[Dict[str, Any]]) -> List[str]:
        names = [str(character["name"]) for character in characters]
        scene_names = [str(name) for name in outline.get("characters", []) if str(name) in names]
        return scene_names or names[:1]
