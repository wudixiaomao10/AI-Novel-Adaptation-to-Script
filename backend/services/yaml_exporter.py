import yaml

from schemas.script_schema import Script


def export_script_to_yaml(script: Script) -> str:
    """Export a Script object as YAML with a top-level script key."""
    payload = {"script": script.model_dump(mode="json")}
    return yaml.dump(payload, allow_unicode=True, sort_keys=False)

