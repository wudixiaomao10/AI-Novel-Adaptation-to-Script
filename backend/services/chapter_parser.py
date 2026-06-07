import re
from typing import Dict, List


Chapter = Dict[str, str | int]

CHAPTER_HEADING_PATTERN = re.compile(
    r"^\s*(?:"
    r"第\s*[0-9零〇一二三四五六七八九十百千万两]+\s*[章节卷回篇]\s*[^\n]*"
    r"|Chapter\s+\d+(?:\s*[:：.-]\s*[^\n]+)?"
    r")\s*$",
    re.IGNORECASE,
)


def split_chapters(text: str) -> List[Chapter]:
    """Split novel text into titled chapters or short-story scene units."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    lines = normalized.split("\n")
    heading_positions = [
        index
        for index, line in enumerate(lines)
        if CHAPTER_HEADING_PATTERN.match(line.strip())
    ]

    if heading_positions:
        return _split_by_headings(lines, heading_positions)

    return _split_short_story(normalized)


def validate_min_chapters(chapters: List[Chapter], min_count: int = 1) -> None:
    """Raise ValueError when no usable story unit was parsed."""
    if len(chapters) < min_count:
        raise ValueError("Novel text cannot be empty.")


def _split_by_headings(lines: List[str], heading_positions: List[int]) -> List[Chapter]:
    chapters: List[Chapter] = []

    for offset, start in enumerate(heading_positions):
        end = heading_positions[offset + 1] if offset + 1 < len(heading_positions) else len(lines)
        title = lines[start].strip()
        content = "\n".join(lines[start + 1 : end]).strip()
        chapters.append(
            {
                "chapter_index": offset + 1,
                "title": title,
                "content": content,
            }
        )

    return chapters


def _split_short_story(text: str) -> List[Chapter]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    if not paragraphs:
        return []

    if len(paragraphs) == 1:
        return _split_single_block(paragraphs[0])

    return [
        {
            "chapter_index": index + 1,
            "title": f"短篇段落 {index + 1}",
            "content": paragraph,
        }
        for index, paragraph in enumerate(paragraphs)
    ]


def _split_single_block(text: str) -> List[Chapter]:
    if len(text) <= 1200:
        return [
            {
                "chapter_index": 1,
                "title": "短篇小说",
                "content": text,
            }
        ]

    chunks = _split_by_sentences(text, max_length=900)
    return [
        {
            "chapter_index": index + 1,
            "title": f"短篇片段 {index + 1}",
            "content": chunk,
        }
        for index, chunk in enumerate(chunks)
    ]


def _split_by_sentences(text: str, max_length: int) -> List[str]:
    sentences = [part for part in re.split(r"(?<=[。！？!?])", text) if part.strip()]
    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        if current and len(current) + len(sentence) > max_length:
            chunks.append(current.strip())
            current = sentence
        else:
            current += sentence

    if current.strip():
        chunks.append(current.strip())

    if not chunks:
        return [text]
    return chunks

