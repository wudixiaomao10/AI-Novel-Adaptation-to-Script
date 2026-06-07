import json
from typing import Any, Dict, List


Chapter = Dict[str, str | int]

FEW_SHOT_SOURCE = (
    "冷西军挥起斧头狠狠砸向煤墙，时而迸出火星。他心里满是愤怒。"
    "老工长张昆叹了口气，对他说：“歇会儿吧，留点力气。”"
)

FEW_SHOT_SCENE = {
    "id": "scene_example",
    "chapter": 1,
    "title": "破壁求生",
    "location": "地底死角",
    "time": "震后八小时",
    "mood": "压抑、愤怒",
    "summary": "冷西军疯狂砍击煤墙发泄愤怒，张昆劝阻。",
    "characters": ["冷西军", "张昆"],
    "beats": [
        {
            "type": "action",
            "text": "冷西军抡起斧头，狠狠向坚硬的煤帮劈去，火星四溅。",
        },
        {
            "type": "dialogue",
            "character": "张昆",
            "emotion": "疲惫但威严",
            "text": "歇会儿吧，留点力气。",
        },
    ],
}


def build_outline_prompt(
    title: str,
    chapters: List[Chapter],
    generation_options: Dict[str, Any] | None = None,
) -> str:
    """Build the first-stage prompt for characters and scene outline."""
    chapter_payload = json.dumps(chapters, ensure_ascii=False, indent=2)
    options_payload = json.dumps(generation_options or {}, ensure_ascii=False, indent=2)
    example_scene = json.dumps(
        {
            "characters": [
                {
                    "id": "char_001",
                    "name": "冷西军",
                    "role": "protagonist",
                    "description": "被困矿工，情绪激烈，求生意志强。",
                    "traits": ["愤怒", "顽强"],
                },
                {
                    "id": "char_002",
                    "name": "张昆",
                    "role": "supporting",
                    "description": "老工长，疲惫但保持判断力。",
                    "traits": ["沉稳", "威严"],
                },
            ],
            "scenes": [
                {
                    key: value
                    for key, value in FEW_SHOT_SCENE.items()
                    if key != "beats"
                }
            ],
        },
        ensure_ascii=False,
        indent=2,
    )

    return f"""
Role: You are an elite screenwriter and AI story analyst.
Task: Analyze the Chinese novel text and output ONLY a valid JSON object.

This is stage 1 of a multi-step pipeline. Do NOT write beats yet.
Only produce:
- a stable character table
- a scene outline split by major shifts in location, time, emotional dynamic, or dramatic goal

JSON shape:
{{
  "characters": [
    {{
      "id": "char_001",
      "name": "角色名字",
      "role": "protagonist/supporting/minor",
      "description": "角色简要介绍",
      "traits": ["性格标签"]
    }}
  ],
  "scenes": [
    {{
      "id": "scene_001",
      "chapter": 1,
      "title": "场景标题",
      "location": "具体地点",
      "time": "白天/夜晚/深夜/清晨/未知时间等",
      "mood": "紧张/悲伤/绝望/悬疑等氛围",
      "summary": "本场戏的核心剧情摘要",
      "characters": ["本场出现的角色名字"]
    }}
  ]
}}

Critical rules:
1. Do not copy the prose as-is. Condense it into dramatic scenes.
2. Split scenes whenever time, location, dramatic goal, or character dynamic changes.
3. For short stories without chapters, still create scenes if the dramatic action changes.
4. Keep character names consistent across all scenes.
5. Output raw JSON only. Do not wrap in Markdown.

Few-shot input:
{FEW_SHOT_SOURCE}

Few-shot output:
{example_scene}

Title: {title}
Generation options:
{options_payload}

Source chapters or short-story units:
{chapter_payload}
""".strip()


def build_scene_beats_prompt(
    title: str,
    characters: List[Dict[str, Any]],
    scene_outline: Dict[str, Any],
    source_text: str,
    generation_options: Dict[str, Any] | None = None,
) -> str:
    """Build the second-stage prompt for one scene's screenplay beats."""
    characters_payload = json.dumps(characters, ensure_ascii=False, indent=2)
    scene_payload = json.dumps(scene_outline, ensure_ascii=False, indent=2)
    options_payload = json.dumps(generation_options or {}, ensure_ascii=False, indent=2)
    example = json.dumps({"beats": FEW_SHOT_SCENE["beats"]}, ensure_ascii=False, indent=2)

    return f"""
Role: You are an elite screenwriter.
Task: Convert one planned scene into screenplay beats.

Output ONLY a valid JSON object with this shape:
{{
  "beats": [
    {{
      "type": "action",
      "text": "动作调度或环境描写",
      "character": null,
      "emotion": null
    }},
    {{
      "type": "dialogue",
      "character": "说话人名字",
      "emotion": "语气/神态",
      "text": "台词内容"
    }}
  ]
}}

Critical adaptation rules:
1. DO NOT copy prose mechanically. Translate inner thoughts into visible action, dialogue, or narration.
2. beats.type MUST ONLY be one of: action, dialogue, narration, transition.
3. Dialogue beats MUST include character.
4. Use only characters from the character table unless the source clearly introduces someone new.
5. Generate 4 to 8 beats for the scene when possible.
6. Output raw JSON only. No Markdown.

Few-shot input:
{FEW_SHOT_SOURCE}

Few-shot output:
{example}

Script title: {title}
Generation options:
{options_payload}

Character table:
{characters_payload}

Scene outline:
{scene_payload}

Source text for this scene:
\"\"\"
{source_text}
\"\"\"
""".strip()


def build_script_prompt(title: str, chapters: List[Chapter]) -> str:
    """Build a legacy full-script prompt for compatibility."""
    return build_outline_prompt(title=title, chapters=chapters)
