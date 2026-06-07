from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Character(BaseModel):
    """A character appearing in the adapted script."""

    id: str
    name: str
    role: str
    description: Optional[str] = None
    traits: List[str] = Field(default_factory=list)


class Beat(BaseModel):
    """A single action, dialogue, narration, or transition inside a scene."""

    type: Literal["action", "dialogue", "narration", "transition"]
    text: str
    character: Optional[str] = None
    emotion: Optional[str] = None

    @model_validator(mode="after")
    def validate_dialogue_character(self) -> "Beat":
        """Require dialogue beats to include a speaking character."""
        if self.type == "dialogue" and not self.character:
            raise ValueError("dialogue beat must include character")
        return self


class Scene(BaseModel):
    """A structured scene generated from a novel chapter."""

    id: str
    chapter: int = Field(ge=1)
    title: str
    location: str
    time: str
    mood: Optional[str] = None
    summary: str
    characters: List[str] = Field(default_factory=list)
    beats: List[Beat] = Field(min_length=1)


class Script(BaseModel):
    """The complete script structure returned by the conversion pipeline."""

    title: str
    source_type: str = "novel"
    version: str = "0.1"
    language: str = "zh-CN"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    characters: List[Character] = Field(min_length=1)
    scenes: List[Scene] = Field(min_length=1)


class ScriptResponse(BaseModel):
    """API response containing the YAML script draft."""

    success: bool
    script_yaml: str
    script_data: Optional[Dict[str, Any]] = None
