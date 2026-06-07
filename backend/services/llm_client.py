import asyncio
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class LLMSettings:
    """Runtime settings for optional real LLM generation."""

    provider: str
    api_key: str | None
    base_url: str
    model: str
    timeout_seconds: float
    temperature: float
    max_retries: int
    json_mode: bool
    use_proxy: bool

    @classmethod
    def from_env(cls) -> "LLMSettings":
        """Load LLM settings from environment variables."""
        provider = os.getenv("NOVEL2SCRIPT_LLM_PROVIDER", "mock").strip().lower()
        base_url = os.getenv("NOVEL2SCRIPT_LLM_BASE_URL") or _default_base_url(provider)
        model = os.getenv("NOVEL2SCRIPT_LLM_MODEL") or _default_model(provider)

        return cls(
            provider=provider,
            api_key=os.getenv("NOVEL2SCRIPT_LLM_API_KEY"),
            base_url=base_url.rstrip("/"),
            model=model,
            timeout_seconds=float(os.getenv("NOVEL2SCRIPT_LLM_TIMEOUT", "45")),
            temperature=float(os.getenv("NOVEL2SCRIPT_LLM_TEMPERATURE", "0.3")),
            max_retries=int(os.getenv("NOVEL2SCRIPT_LLM_MAX_RETRIES", "2")),
            json_mode=os.getenv("NOVEL2SCRIPT_LLM_JSON_MODE", "true").strip().lower()
            not in {"0", "false", "no", "off"},
            use_proxy=os.getenv("NOVEL2SCRIPT_LLM_USE_PROXY", "false").strip().lower()
            in {"1", "true", "yes", "on"},
        )


class LLMClient:
    """OpenAI-compatible JSON generation client with mock mode by default."""

    def __init__(self, settings: LLMSettings | None = None) -> None:
        self.settings = settings or LLMSettings.from_env()

    @property
    def is_enabled(self) -> bool:
        """Return True when a real LLM provider is configured."""
        return self.settings.provider not in {"", "mock", "none", "local_mock"}

    async def complete_json(self, prompt: str) -> Dict[str, Any]:
        """Call a real LLM and parse its response as a JSON object."""
        if not self.is_enabled:
            raise RuntimeError("LLM provider is mock; real completion is disabled.")
        if not self.settings.api_key:
            raise RuntimeError("NOVEL2SCRIPT_LLM_API_KEY is required for real LLM generation.")
        if self.settings.provider not in {"openai", "openai_compatible", "deepseek", "qwen"}:
            raise RuntimeError(f"Unsupported LLM provider: {self.settings.provider}")

        return await asyncio.to_thread(self._complete_json_sync, prompt)

    def _complete_json_sync(self, prompt: str) -> Dict[str, Any]:
        endpoint = f"{self.settings.base_url}/chat/completions"
        payload = {
            "model": self.settings.model,
            "temperature": self.settings.temperature,
            "messages": [
                {
                    "role": "system",
                    "content": "You convert novels into strict JSON screenplay data. Return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        if self.settings.json_mode:
            payload["response_format"] = {"type": "json_object"}

        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        data: Dict[str, Any] | None = None
        last_error: Exception | None = None
        opener = (
            urllib.request.build_opener()
            if self.settings.use_proxy
            else urllib.request.build_opener(urllib.request.ProxyHandler({}))
        )
        for attempt in range(self.settings.max_retries + 1):
            try:
                with opener.open(request, timeout=self.settings.timeout_seconds) as response:
                    data = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code < 500 or attempt >= self.settings.max_retries:
                    raise RuntimeError(f"LLM HTTP error {exc.code}: {body}") from exc
                last_error = exc
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt >= self.settings.max_retries:
                    raise RuntimeError(f"LLM network error: {exc.reason}") from exc

        if data is None:
            raise RuntimeError(f"LLM request failed: {last_error}")

        content = data["choices"][0]["message"]["content"]
        return _parse_json_object(content)

    def status(self) -> Dict[str, Any]:
        """Return safe status data for UI and health checks."""
        return {
            "provider": self.settings.provider,
            "enabled": self.is_enabled,
            "configured": bool(self.settings.api_key) if self.is_enabled else True,
            "base_url": self.settings.base_url,
            "model": self.settings.model,
            "json_mode": self.settings.json_mode,
            "use_proxy": self.settings.use_proxy,
            "timeout_seconds": self.settings.timeout_seconds,
            "max_retries": self.settings.max_retries,
        }


def _parse_json_object(content: str) -> Dict[str, Any]:
    """Parse a JSON object from plain text or fenced model output."""
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)

    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object.")
    return parsed


def _default_base_url(provider: str) -> str:
    if provider == "deepseek":
        return "https://api.deepseek.com/v1"
    if provider == "qwen":
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"
    return "https://api.openai.com/v1"


def _default_model(provider: str) -> str:
    if provider == "deepseek":
        return "deepseek-chat"
    if provider == "qwen":
        return "qwen-plus"
    return "gpt-4o-mini"
