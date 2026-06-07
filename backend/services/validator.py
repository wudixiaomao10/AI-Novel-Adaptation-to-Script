from typing import Any, Dict

from pydantic import ValidationError

from schemas.script_schema import Script


def validate_script_data(data: Dict[str, Any]) -> Script:
    """Validate raw script data and return a Script object."""
    try:
        payload = data.get("script", data)
        return Script.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Script validation failed: {exc}") from exc
