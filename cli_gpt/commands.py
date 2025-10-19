"""Slash command handling for the cli-gpt application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import ModelManager


HELP_TEXT = (
    "/model [name]  Switch to a different free model\n"
    "/list          List available free models\n"
    "/clear         Clear chat history\n"
    "/help          really?\n"
    "/quit, /exit   Exit the application"
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
        if command == "list":
            return CommandResult(handled=True, show_models=True)
        if command == "model":
            return self._handle_model(argument)
        if command == "clear":
            return CommandResult(handled=True, clear_history=True, message="Chat history cleared.")

        return CommandResult(handled=True, message=f"Unknown command: /{command}. Type /help.")

    def _handle_model(self, argument: str) -> CommandResult:
        if not argument:
            current = self.model_manager.current_model
            return CommandResult(
                handled=True,
                message=f"Current model: {current}\nUse /model <name> to switch.",
            )
        try:
            self.model_manager.set_model(argument)
        except ValueError as exc:
            return CommandResult(handled=True, message=str(exc))

        return CommandResult(
            handled=True,
            message=f"Switched model to {self.model_manager.current_model}",
        )
