"""OpenRouter API wrapper."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
MODELS_URL = os.getenv("OPENROUTER_MODELS_URL", "https://openrouter.ai/api/v1/models")
APP_TITLE = (
    os.getenv("CLI_GPT_APP_TITLE")
    or os.getenv("CLI_CHAT_APP_TITLE")
    or "cli-gpt"
)
APP_REFERER = (
    os.getenv("CLI_GPT_APP_REFERER")
    or os.getenv("CLI_CHAT_APP_REFERER")
    or "https://github.com/aoyn1xw/cli-gpt"
)


class MissingAPIKeyError(RuntimeError):
    """Raised when an API key is required but not provided."""


class OpenRouterAPIError(RuntimeError):
    """Raised when the OpenRouter API returns an error response."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"OpenRouter API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message


@dataclass
class OpenRouterClient:
    """Simple client for the OpenRouter API."""

    api_key: str
    timeout: int = 45
    session: Optional[requests.Session] = None

    def __post_init__(self) -> None:
        if not self.api_key:
            raise MissingAPIKeyError(
                "OPENROUTER_API_KEY is not set. Please export it before running cli-gpt."
            )
        if self.session is None:
            self.session = requests.Session()

    def chat_completion(self, messages: List[Dict[str, Any]], model: str) -> str:
        payload = {"model": model, "messages": messages}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": APP_REFERER,
            "X-Title": APP_TITLE,
        }

        try:
            response = self.session.post(
                API_URL,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:  # pragma: no cover - network issue
            raise RuntimeError(f"Network error: {exc}") from exc

        if not response.ok:
            self._raise_api_error(response)

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Unexpected API response format.") from exc

    def list_models(self, *, free_only: bool = True) -> List[str]:
        """Fetch available models from the OpenRouter catalogue."""
        return fetch_models_catalogue(
            api_key=self.api_key,
            timeout=self.timeout,
            free_only=free_only,
            session=self.session,
        )

    @staticmethod
    def _raise_api_error(response: requests.Response) -> None:
        message = "Unknown error"
        try:
            body = response.json()
            message = body.get("error", {}).get("message") or body.get("message") or message
        except ValueError:
            if response.text:
                message = response.text.strip()
        raise OpenRouterAPIError(response.status_code, message)


def get_api_key() -> str:
    """Fetch the API key from the environment or raise a clear error."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise MissingAPIKeyError(
            "Missing OPENROUTER_API_KEY environment variable. "
            "Set it before running cli-gpt."
        )
    return key


def fetch_models_catalogue(
    *,
    api_key: Optional[str] = None,
    timeout: int = 45,
    free_only: bool = True,
    session: Optional[requests.Session] = None,
) -> List[str]:
    """Fetch model ids from OpenRouter, optionally without auth for public catalogue access."""
    active_session = session or requests.Session()
    headers = {
        "HTTP-Referer": APP_REFERER,
        "X-Title": APP_TITLE,
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = active_session.get(
            MODELS_URL,
            headers=headers,
            timeout=timeout,
        )
    except requests.RequestException as exc:  # pragma: no cover - network issue
        raise RuntimeError(f"Network error while fetching models: {exc}") from exc

    if not response.ok:
        OpenRouterClient._raise_api_error(response)

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Unexpected model list response format.") from exc

    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError("Model list payload missing 'data' array.")

    models: List[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not isinstance(model_id, str):
            continue
        if free_only and not _is_model_free(model_id=model_id, pricing=item.get("pricing")):
            continue
        models.append(model_id)

    # Preserve order but remove duplicates.
    seen = set()
    deduped: List[str] = []
    for model_id in models:
        if model_id in seen:
            continue
        seen.add(model_id)
        deduped.append(model_id)
    return deduped


def _is_model_free(*, model_id: str, pricing: Any) -> bool:
    if model_id.lower().endswith(":free"):
        return True
    if not isinstance(pricing, dict):
        return False
    prompt_price = pricing.get("prompt")
    completion_price = pricing.get("completion")
    return _is_zero_cost(prompt_price) and _is_zero_cost(completion_price)


def _is_zero_cost(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return float(value) == 0.0
    if isinstance(value, str):
        trimmed = value.strip().lower()
        if not trimmed:
            return False
        if trimmed in {"0", "0.0", "0.00", "free"}:
            return True
        try:
            return float(trimmed) == 0.0
        except ValueError:
            return False
    return False
