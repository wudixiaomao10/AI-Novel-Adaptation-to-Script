from typing import Any, Dict, List


def write_scene_beats(scene_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Write action, dialogue, narration, and transition beats for a scene plan."""
    protagonist = scene_plan["characters"][0]
    events = scene_plan.get("events") or []
    dialogues = scene_plan.get("dialogues") or []
    opening_action = events[0] if events else f"{protagonist}进入{scene_plan['location']}，故事冲突开始显现"
    narration = scene_plan["summary"]
    dialogue = dialogues[0] if dialogues else _fallback_dialogue(scene_plan.get("mood"))

    return [
        {
            "type": "action",
            "text": _ensure_sentence(opening_action),
            "character": None,
            "emotion": None,
        },
        {
            "type": "dialogue",
            "text": dialogue,
            "character": protagonist,
            "emotion": _emotion_from_mood(scene_plan.get("mood")),
        },
        {
            "type": "narration",
            "text": _ensure_sentence(narration),
            "character": None,
            "emotion": None,
        },
        {
            "type": "transition",
            "text": f"镜头从{scene_plan['location']}继续推进，新的压力开始出现。",
            "character": None,
            "emotion": None,
        },
    ]


def _ensure_sentence(text: str) -> str:
    compact = text.strip()
    if not compact:
        return "场景信息被整理为可继续编辑的剧本节拍。"
    if compact[-1] not in "。！？!?":
        return f"{compact}。"
    return compact


def _emotion_from_mood(mood: str | None) -> str:
    if mood == "悬疑":
        return "警觉"
    if mood == "紧张":
        return "压抑"
    return "克制"


def _fallback_dialogue(mood: str | None) -> str:
    if mood == "悬疑":
        return "这里不对劲。"
    if mood == "紧张":
        return "别再往前了。"
    return "我们得继续。"

