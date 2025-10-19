"""Model management for the cli-gpt app."""

from dataclasses import dataclass, field
from typing import Iterable, List

FREE_MODELS: List[str] = [
    "qwen/qwen3-235b-a22b:free",
    "ArliAI/QwQ-32B-RpR-v1",
    "Google/Gemma-2-9B",
    "Google/Gemma-3-12B",
    "Google/Gemma-3n-2B",
    "Google/Gemma-3-4B",
    "Google/Gemma-3n-4B",
    "Tencent/Hunyuan-A13B-Instruct",
    "Agentica/Deepcoder-14B-Preview",
]

DEFAULT_MODEL: str = "qwen/qwen3-235b-a22b:free"


@dataclass
class ModelManager:
    """Maintain the currently selected model."""

    available_models: List[str] = field(default_factory=lambda: list(FREE_MODELS))
    current_model: str = DEFAULT_MODEL

    def __post_init__(self) -> None:
        if not self.available_models:
            self.available_models = list(FREE_MODELS)
        if self.current_model not in self.available_models:
            self.current_model = self.available_models[0]

    def set_model(self, name: str) -> None:
        if name not in self.available_models:
            raise ValueError(f"Model '{name}' is not available in free tier.")
        self.current_model = name

    def list_models(self) -> List[str]:
        return list(self.available_models)

    def replace_models(self, models: Iterable[str]) -> None:
        new_models: List[str] = []
        seen = set()
        for model in models:
            if not isinstance(model, str):
                continue
            if model in seen:
                continue
            seen.add(model)
            new_models.append(model)

        if not new_models:
            return

        self.available_models = new_models
        if self.current_model not in self.available_models:
            self.current_model = self.available_models[0]
