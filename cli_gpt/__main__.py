"""Entry point for the cli-gpt package."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__
from .models import FREE_MODELS
from .ui import run_cli


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point when executed via `python -m cli_gpt` or the console script."""
    parser = argparse.ArgumentParser(
        prog="cli-gpt",
        description="Chat with OpenRouter free-tier models from your terminal.",
    )
    parser.add_argument(
        "--model",
        choices=FREE_MODELS,
        help=f"Select the initial model (default: {FREE_MODELS[0]}).",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Display all available free-tier models and exit.",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Disable rich formatting for minimal/plain output.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Override the request timeout in seconds (default: 45).",
    )
    parser.add_argument(
        "--api-key",
        help="Provide the OpenRouter API key explicitly (overrides environment variable).",
    )
    fullscreen_group = parser.add_mutually_exclusive_group()
    fullscreen_group.add_argument(
        "--fullscreen",
        dest="fullscreen",
        action="store_true",
        help="Force full-screen terminal mode.",
    )
    fullscreen_group.add_argument(
        "--no-fullscreen",
        dest="fullscreen",
        action="store_false",
        help="Disable full-screen terminal mode.",
    )
    parser.set_defaults(fullscreen=None)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args(argv)

    if args.timeout is not None and args.timeout <= 0:
        parser.error("--timeout must be greater than zero seconds.")

    if args.list_models:
        for name in FREE_MODELS:
            print(name)
        return 0

    return run_cli(
        model=args.model,
        api_key=args.api_key,
        timeout=args.timeout,
        plain_output=args.plain,
        full_screen=args.fullscreen,
    )


if __name__ == "__main__":
    sys.exit(main())
