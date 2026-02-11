"""Slash command handling for the cli-gpt application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import ModelManager


HELP_TEXT = (
    "Available commands:\n"
    "/help            Show this help message\n"
    "/switch [model]  Switch to another model (no argument opens selector)\n"
    "/new             Start a new chat (clears message history)\n"
    "/quit            Exit cli-gpt"
)


@dataclass
class CommandResult:
    handled: bool
    exit: bool = False
    message: Optional[str] = None
    clear_history: bool = False
    show_models: bool = False


class CommandProcessor:
    """Parse and execute slash commands."""

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager

    def process(self, text: str) -> CommandResult:
        if not text.startswith("/"):
            return CommandResult(handled=False)

        command_parts = text[1:].strip().split(maxsplit=1)
        if not command_parts:
            return CommandResult(handled=True, message="Empty command. Type /help for options.")

        command = command_parts[0].lower()
        argument = command_parts[1].strip() if len(command_parts) > 1 else ""

        if command in {"quit", "exit"}:
            return CommandResult(handled=True, exit=True)
        if command == "help":
            return CommandResult(handled=True, message=HELP_TEXT)
        if command in {"switch", "model"}:
            return self._handle_switch(argument)
        if command in {"new", "clear"}:
            return CommandResult(handled=True, clear_history=True, message="Started a new chat.")
        if command == "list":
            return CommandResult(
                handled=True,
                show_models=True,
                message="Tip: use /switch to pick a model.",
            )

        return CommandResult(handled=True, message=f"Unknown command: /{command}. Type /help.")

    def _handle_switch(self, argument: str) -> CommandResult:
        if not argument:
            return CommandResult(handled=True, show_models=True)

        try:
            self.model_manager.set_model(argument)
        except ValueError as exc:
            return CommandResult(handled=True, message=str(exc))

        return CommandResult(
            handled=True,
            message=f"Switched model to {self.model_manager.current_model}",
        )
