from typing import Any, Dict, List


Chapter = Dict[str, str | int]


def plan_scenes(facts: Dict[str, Any], chapters: List[Chapter]) -> List[Dict[str, Any]]:
    """Plan editable scenes from extracted facts."""
    characters = facts["characters"]
    protagonist = characters[0]["name"]
    supporting = characters[1]["name"] if len(characters) > 1 else protagonist
    plans: List[Dict[str, Any]] = []

    if len(chapters) == 1:
        short_story_plans = _plan_short_story_scenes(
            facts=facts,
            protagonist=protagonist,
            supporting=supporting,
        )
        if short_story_plans:
            return short_story_plans

    for index, chapter_fact in enumerate(facts["chapter_facts"], start=1):
        is_final = index == len(chapters)
        scene_characters = [protagonist]
        if is_final and supporting not in scene_characters:
            scene_characters.append(supporting)

        plans.append(
            {
                "id": f"scene_{index:03d}",
                "chapter": chapter_fact["chapter_index"],
                "title": _scene_title(chapter_fact["title"], index),
                "location": chapter_fact["location"],
                "time": chapter_fact["time"],
                "mood": chapter_fact["mood"],
                "summary": chapter_fact["summary"],
                "characters": scene_characters,
                "events": chapter_fact["events"],
                "dialogues": chapter_fact["dialogues"],
            }
        )

    return plans


def _plan_short_story_scenes(
    facts: Dict[str, Any],
    protagonist: str,
    supporting: str,
) -> List[Dict[str, Any]]:
    chapter_fact = facts["chapter_facts"][0]
    events = chapter_fact.get("events") or []
    dialogues = chapter_fact.get("dialogues") or []

    if len(events) <= 1:
        return []

    plans: List[Dict[str, Any]] = []
    scene_events = events[:4]

    for index, event in enumerate(scene_events, start=1):
        scene_characters = [protagonist]
        if index == len(scene_events) and supporting not in scene_characters:
            scene_characters.append(supporting)

        plans.append(
            {
                "id": f"scene_{index:03d}",
                "chapter": chapter_fact["chapter_index"],
                "title": _short_scene_title(index, event),
                "location": chapter_fact["location"],
                "time": chapter_fact["time"],
                "mood": chapter_fact["mood"],
                "summary": event,
                "characters": scene_characters,
                "events": [event],
                "dialogues": dialogues[index - 1 : index] or dialogues[:1],
            }
        )

    return plans


def _scene_title(chapter_title: str, index: int) -> str:
    clean_title = chapter_title.strip()
    return clean_title if clean_title else f"Scene {index}"


def _short_scene_title(index: int, event: str) -> str:
    compact = event.strip()
    if compact:
        return compact[:14]
    return f"短篇场景 {index}"

