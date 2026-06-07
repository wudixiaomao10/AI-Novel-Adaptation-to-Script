import re
from typing import Any, Dict, List


Chapter = Dict[str, str | int]

ACTION_VERBS = (
    "推开",
    "握紧",
    "走进",
    "走上",
    "走出",
    "打开",
    "看见",
    "发现",
    "听见",
    "来到",
    "低声",
    "说",
    "问",
)

STOP_WORDS = {
    "发现",
    "推开",
    "屋里",
    "一片",
    "楼上",
    "传来",
    "终于",
    "这里",
    "有人",
    "旧宅",
    "大门",
    "低声",
    "缓慢",
    "影中",
    "阴影",
    "手电",
    "脚步",
}


def extract_story_facts(title: str, chapters: List[Chapter]) -> Dict[str, Any]:
    """Extract lightweight story facts for the enhanced mock pipeline."""
    all_text = "\n".join(str(chapter.get("content") or "") for chapter in chapters)
    character_names = _extract_character_names(all_text)

    if not character_names:
        character_names = ["主角"]
    if len(character_names) == 1:
        character_names.append("关键人物")

    characters = [
        {
            "id": f"char_{index:03d}",
            "name": name,
            "role": "protagonist" if index == 1 else "supporting",
            "description": _character_description(index, name),
            "traits": _character_traits(index),
        }
        for index, name in enumerate(character_names[:4], start=1)
    ]

    chapter_facts = [
        {
            "chapter_index": int(chapter.get("chapter_index") or index),
            "title": str(chapter.get("title") or f"Chapter {index}"),
            "summary": _summarize(str(chapter.get("content") or ""), fallback=f"{title}的第{index}段剧情"),
            "dialogues": _extract_dialogues(str(chapter.get("content") or "")),
            "location": _guess_location(str(chapter.get("title") or ""), str(chapter.get("content") or "")),
            "time": _guess_time(str(chapter.get("content") or "")),
            "mood": _guess_mood(str(chapter.get("content") or "")),
            "events": _extract_events(str(chapter.get("content") or "")),
        }
        for index, chapter in enumerate(chapters, start=1)
    ]

    return {
        "title": title,
        "source_chapter_count": len(chapters),
        "characters": characters,
        "chapter_facts": chapter_facts,
    }


def _extract_character_names(text: str) -> List[str]:
    names: List[str] = []
    verb_pattern = "|".join(re.escape(verb) for verb in ACTION_VERBS)
    for match in re.finditer(rf"([\u4e00-\u9fff]{{2,4}})(?:{verb_pattern})", text):
        candidate = _clean_name(match.group(1))
        if candidate and candidate not in names:
            names.append(candidate)

    for match in re.finditer(r"([\u4e00-\u9fff]{2,4})(?:从|自|在|向)", text):
        candidate = _clean_name(match.group(1))
        if candidate and candidate not in names:
            names.append(candidate)

    for match in re.finditer(r"[“「『](.{1,40}?)[”」』]", text):
        before = text[max(0, match.start() - 12) : match.start()]
        speaker_match = re.search(r"([\u4e00-\u9fff]{2,4})(?:说|问|低声问|喊|回答)[:：]?\s*$", before)
        if speaker_match:
            candidate = _clean_name(speaker_match.group(1))
            if candidate and candidate not in names:
                names.append(candidate)

    return names


def _clean_name(value: str) -> str | None:
    name = value.strip(" ，。；：、“”「」『』")
    if len(name) > 2 and name[0] in {"她", "他", "它"}:
        name = name[1:]
    if name.endswith(("低声", "缓慢", "阴影", "影中", "楼上")):
        return None
    if len(name) > 2:
        name = name[-2:]
    if len(name) < 2 or name in STOP_WORDS:
        return None
    return name


def _extract_dialogues(text: str) -> List[str]:
    return [match.group(1).strip() for match in re.finditer(r"[“「『](.{1,80}?)[”」』]", text)]


def _extract_events(text: str) -> List[str]:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"[。！？!?]\s*", text)
        if sentence.strip()
    ]
    return sentences[:4]


def _guess_location(title: str, content: str) -> str:
    combined = f"{title}\n{content}"
    location_keywords = ("旧宅", "客厅", "走廊", "楼梯", "二楼", "房间", "门外", "街道", "森林", "宫殿")
    for keyword in location_keywords:
        if keyword in combined:
            return keyword
    return "主要场景"


def _guess_time(content: str) -> str:
    if any(keyword in content for keyword in ("夜", "深夜", "月光", "黑")):
        return "夜晚"
    if any(keyword in content for keyword in ("清晨", "黎明", "晨光")):
        return "清晨"
    if any(keyword in content for keyword in ("黄昏", "傍晚", "夕阳")):
        return "傍晚"
    return "未知时间"


def _guess_mood(content: str) -> str:
    if any(keyword in content for keyword in ("漆黑", "脚步", "阴影", "秘密", "颤")):
        return "悬疑"
    if any(keyword in content for keyword in ("争吵", "愤怒", "冲突")):
        return "紧张"
    return "推进"


def _summarize(text: str, fallback: str) -> str:
    compact = " ".join(text.split())
    return compact[:90] if compact else fallback


def _character_description(index: int, name: str) -> str:
    if index == 1:
        return f"{name}是故事主角，承担探索、选择和推动剧情的功能。"
    return f"{name}与主线冲突相关，为剧情提供线索或阻力。"


def _character_traits(index: int) -> List[str]:
    return ["敏感", "勇敢"] if index == 1 else ["神秘", "冷静"]
