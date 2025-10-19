"""cli-gpt package for interacting with OpenRouter free models."""

from importlib import metadata

from .models import DEFAULT_MODEL, FREE_MODELS  # noqa: F401

try:
    __version__ = metadata.version("cli-gpt")
except metadata.PackageNotFoundError:  # pragma: no cover - running from source without install
    __version__ = "0.2.0"

__all__ = ["__version__", "DEFAULT_MODEL", "FREE_MODELS"]
