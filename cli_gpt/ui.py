"""Terminal user interface for the cli-gpt app."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, ScrollOffsets
from prompt_toolkit.layout.containers import ConditionalContainer, HSplit, VSplit, Window, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel

from .api import MissingAPIKeyError, OpenRouterClient, get_api_key
from .commands import CommandProcessor
from .models import ModelManager

SYSTEM_PROMPT = {
    "role": "system",
    "content": "you are a General purpose AI assistant. Answer as concisely as possible. BUT DO MAKE UP FALSE FACTS IF YOU DONT KNOW THE ANSWER SAY YOU DONT KNOW IT",
}


@dataclass
class ChatState:
    """Track chat history."""

    history: List[Dict[str, Any]] = field(default_factory=lambda: [SYSTEM_PROMPT.copy()])

    def reset(self) -> None:
        self.history = [SYSTEM_PROMPT.copy()]

    def add_user_message(self, content: str) -> None:
        self.history.append({"role": "user", "content": content})

    def add_ai_message(self, content: str) -> None:
        self.history.append({"role": "assistant", "content": content})

    def messages(self) -> List[Dict[str, Any]]:
        # Return a shallow copy to avoid accidental mutation.
        return list(self.history)


class ChatApp:
    """Main application controller."""

    def __init__(
        self,
        *,
        initial_model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        plain_output: bool = False,
        session: Optional[PromptSession] = None,
        full_screen: Optional[bool] = None,
    ) -> None:
        self._use_rich_rendering = not plain_output
        self.console = _create_console(plain_output)
        self.session = session or PromptSession()
        self.model_manager = ModelManager()
        if initial_model:
            self.model_manager.set_model(initial_model)
        self.state = ChatState()
        self.command_processor = CommandProcessor(self.model_manager)
        self._startup_messages: List[Tuple[str, str]] = []
        if full_screen is None:
            self._full_screen = self._use_rich_rendering and self.console.is_terminal
        else:
            self._full_screen = full_screen and self.console.is_terminal
        self._configure_session()
        self.client = self._init_client(api_key=api_key, timeout=timeout)
        self._refresh_models_from_api()

    def _init_client(self, *, api_key: Optional[str], timeout: Optional[int]) -> OpenRouterClient:
        if timeout is not None and timeout <= 0:
            raise ValueError("Request timeout must be greater than zero seconds.")
        try:
            resolved_key = api_key if api_key is not None else get_api_key()
        except MissingAPIKeyError:
            # Let the caller surface the error using consistent formatting.
            raise

        if timeout is None:
            return OpenRouterClient(api_key=resolved_key)
        return OpenRouterClient(api_key=resolved_key, timeout=timeout)

    def run(self) -> None:
        with patch_stdout(raw=True):
            self._print_status("Ready")
            self._flush_startup_messages()
            while True:
                try:
                    user_input = self.session.prompt("> ")
                except KeyboardInterrupt:
                    self._print_markup(
                        "[bold yellow]Input cancelled. Type /quit to exit.[/bold yellow]",
                        "Input cancelled. Type /quit to exit.",
                    )
                    continue
                except EOFError:
                    # Ctrl+D exits gracefully.
                    break

                stripped = user_input.strip()
                if not stripped:
                    continue

                command_result = self.command_processor.process(stripped)
                if command_result.handled:
                    if command_result.show_models:
                        self._show_models_popup()
                    if command_result.message:
                        self.console.print(command_result.message)
                    if command_result.clear_history:
                        self.state.reset()
                    if command_result.exit:
                        break
                    if stripped.startswith("/model"):
                        self._print_status("Ready")
                    continue

                self._handle_user_message(stripped)

    def _handle_user_message(self, content: str) -> None:
        self.state.add_user_message(content)
        self._print_user_message(content)
        try:
            with self._typing_indicator():
                response_text = self.client.chat_completion(
                    self.state.messages(), model=self.model_manager.current_model
                )
        except MissingAPIKeyError as exc:  # pragma: no cover - indicates configuration drift.
            self._print_markup(f"[bold red]{exc}[/bold red]", f"Error: {exc}")
            raise
        except Exception as exc:  # pragma: no cover - runtime errors
            self._print_markup(f"[bold red]Error:[/bold red] {exc}", f"Error: {exc}")
            return

        self.state.add_ai_message(response_text)
        self._print_ai_message(response_text)
        if response_text.strip() == "I need to check the web for this.":
            follow_up = "Web search not implemented — free mode."
            if self._use_rich_rendering:
                self.console.print(f"[italic cyan]🔍 {follow_up}[/italic cyan]")
            else:
                self.console.print(follow_up)

    def _print_status(self, status: str) -> None:
        model = self.model_manager.current_model
        if self._use_rich_rendering:
            panel = Panel.fit(
                f"Model: [bold]{model}[/bold] | Status: [bold]{status}[/bold]",
                style="cyan",
            )
            self.console.print(panel)
        else:
            self.console.print(f"Model: {model} | Status: {status}")

    def _print_user_message(self, content: str) -> None:
        timestamp = _timestamp()
        if self._use_rich_rendering:
            self.console.print(f"[{timestamp}] [bold blue]You[/bold blue]: {content}")
        else:
            self.console.print(f"[{timestamp}] You: {content}")

    def _print_ai_message(self, content: str) -> None:
        timestamp = _timestamp()
        if self._use_rich_rendering:
            self.console.print(f"[{timestamp}] [bold cyan]AI[/bold cyan]: {content}")
        else:
            self.console.print(f"[{timestamp}] AI: {content}")

    def _print_markup(self, rich_text: str, plain_text: str) -> None:
        if self._use_rich_rendering:
            self.console.print(rich_text)
        else:
            self.console.print(plain_text)

    def _refresh_models_from_api(self, *, notify: bool = False) -> None:
        def emit_message(rich_text: str, plain_text: str) -> None:
            if notify:
                self._print_markup(rich_text, plain_text)
            else:
                self._queue_startup_message(rich_text, plain_text)

        try:
            models = self.client.list_models(free_only=True)
        except Exception as exc:  # pragma: no cover - runtime errors
            emit_message(
                "[bold yellow]Warning:[/bold yellow] Could not refresh free model catalogue.",
                f"Warning: Could not refresh free model catalogue: {exc}",
            )
            return

        if not models:
            emit_message(
                "[bold yellow]Warning:[/bold yellow] OpenRouter did not return any free models.",
                "Warning: OpenRouter did not return any free models.",
            )
            return

        previous_model = self.model_manager.current_model
        self.model_manager.replace_models(models)
        if self.model_manager.current_model != previous_model:
            emit_message(
                (
                    "[bold yellow]Notice:[/bold yellow] Switched to "
                    f"{self.model_manager.current_model} (requested model unavailable)."
                ),
                (
                    "Notice: Switched to "
                    f"{self.model_manager.current_model} (requested model unavailable)."
                ),
            )

    def _queue_startup_message(self, rich_text: str, plain_text: str) -> None:
        self._startup_messages.append((rich_text, plain_text))

    def _flush_startup_messages(self) -> None:
        for rich, plain in self._startup_messages:
            self._print_markup(rich, plain)
        self._startup_messages.clear()

    def _configure_session(self) -> None:
        try:
            self.session.app.full_screen = self._full_screen
        except Exception:  # pragma: no cover - highly unlikely unless internals change
            pass

    @contextmanager
    def _typing_indicator(self):
        message = "AI is thinking..."
        use_status = getattr(self.console, "is_terminal", False)
        if use_status:
            label = f"[cyan]{message}[/cyan]" if self._use_rich_rendering else message
            with self.console.status(label, spinner="dots"):
                yield
        else:
            yield

    def _show_models_popup(self) -> None:
        """Render an interactive model chooser using prompt_toolkit."""
        self._refresh_models_from_api(notify=True)
        models = self.model_manager.list_models()
        if not models:
            self._print_markup(
                "[bold red]No models available to display.[/bold red]",
                "No models available to display.",
            )
            return

        # Fallback for plain output or non-TTY environments.
        if not self._use_rich_rendering or not getattr(self.console, "is_terminal", True):
            formatted = "\n".join(
                f"{'->' if name == self.model_manager.current_model else '  '} {name}"
                for name in models
            )
            self.console.print(f"Available models:\n{formatted}")
            return

        current_model = self.model_manager.current_model
        filter_text = ""
        selected_index = 0

        if current_model in models:
            selected_index = models.index(current_model)

        # Utilities ---------------------------------------------------------
        def filtered_models() -> List[str]:
            if not filter_text:
                return models
            needle = filter_text.lower()
            return [name for name in models if needle in name.lower()]

        def move_selection(delta: int) -> None:
            nonlocal selected_index
            items = filtered_models()
            if not items:
                selected_index = 0
                return
            selected_index = (selected_index + delta) % len(items)

        # Model list view ----------------------------------------------------
        def render_model_list() -> List[Tuple[str, str]]:
            items = filtered_models()
            if not items:
                return [("class:model-list.empty", " No models match your filter.\n")]

            fragments: List[Tuple[str, str]] = []
            for idx, name in enumerate(items):
                # Optional marker for the active model.
                display = f"{name} (current)" if name == current_model else name
                style = "class:model-list"
                if idx == selected_index and name == current_model:
                    style = "class:model-list.selected-current"
                elif idx == selected_index:
                    style = "class:model-list.selected"
                elif name == current_model:
                    style = "class:model-list.current"
                fragments.append((style, f" {display}\n"))
            return fragments

        list_control = FormattedTextControl(render_model_list, show_cursor=False)
        list_window = Window(
            content=list_control,
            always_hide_cursor=True,
            wrap_lines=False,
            height=Dimension(min=8, max=25),
            allow_scroll_beyond_bottom=False,
            scroll_offsets=ScrollOffsets(top=2, bottom=2),
            style="class:model-list-container",
        )

        # Search/filter bar --------------------------------------------------
        search_active = False
        app: Optional[Application] = None

        search_buffer = Buffer()
        search_input_control = BufferControl(buffer=search_buffer, focusable=True)
        search_input_window = Window(
            content=search_input_control,
            height=1,
            always_hide_cursor=False,
            style="class:search.input",
        )
        search_bar = ConditionalContainer(
            VSplit(
                [
                    Window(
                        FormattedTextControl(lambda: [("class:search.prompt", "/ ")]),
                        width=2,
                        dont_extend_width=True,
                    ),
                    search_input_window,
                ]
            ),
            filter=Condition(lambda: search_active or bool(filter_text)),
        )

        # Instruction + footer panels ---------------------------------------
        title_window = Window(
            FormattedTextControl(lambda: [("class:title", "Select a Model")]),
            height=1,
            align=WindowAlign.CENTER,
        )
        hint_window = Window(
            FormattedTextControl(
                lambda: [
                    (
                        "class:footer",
                        "↑/↓ move • Enter select • Esc cancel • / search",
                    )
                ]
            ),
            height=1,
        )

        def update_filter() -> None:
            nonlocal filter_text, selected_index
            filter_text = search_buffer.text.strip()
            items = filtered_models()
            if current_model in items:
                selected_index = items.index(current_model)
            else:
                selected_index = min(selected_index, len(items) - 1) if items else 0
            if app is not None:
                app.invalidate()

        search_buffer.on_text_changed += lambda _: update_filter()

        # Key bindings -------------------------------------------------------
        kb = KeyBindings()

        search_focus = has_focus(search_input_window)

        @kb.add("up", filter=~search_focus)
        def _(event) -> None:
            event.app.layout.focus(list_window)
            move_selection(-1)
            event.app.invalidate()

        @kb.add("down", filter=~search_focus)
        def _(event) -> None:
            event.app.layout.focus(list_window)
            move_selection(1)
            event.app.invalidate()

        @kb.add("pageup", filter=~search_focus)
        def _(event) -> None:
            window = list_window
            info = window.render_info
            if info:
                move_selection(-(max(info.window_height - 1, 1)))
                event.app.invalidate()

        @kb.add("pagedown", filter=~search_focus)
        def _(event) -> None:
            window = list_window
            info = window.render_info
            if info:
                move_selection(max(info.window_height - 1, 1))
                event.app.invalidate()

        @kb.add("/")
        def _(event) -> None:
            nonlocal search_active
            search_active = True
            # Seed the input with the current filter text.
            search_buffer.text = filter_text
            event.app.layout.focus(search_input_window)
            event.app.invalidate()

        @kb.add("enter", filter=has_focus(search_input_window))
        def _(event) -> None:
            nonlocal search_active
            search_active = False
            event.app.layout.focus(list_window)
            event.app.invalidate()

        @kb.add("escape", filter=has_focus(search_input_window))
        def _(event) -> None:
            nonlocal search_active
            search_active = False
            event.app.layout.focus(list_window)
            event.app.invalidate()

        @kb.add("escape")
        def _(event) -> None:
            event.app.exit(result=None)

        @kb.add("enter", filter=~search_focus)
        def _(event) -> None:
            items = filtered_models()
            if not items:
                return
            event.app.exit(result=items[selected_index])

        @kb.add("c-c")
        def _(event) -> None:  # pragma: no cover - user convenience
            event.app.exit(result=None)

        # Compose layout -----------------------------------------------------
        container = HSplit(
            [
                title_window,
                search_bar,
                list_window,
                hint_window,
            ],
            padding=1,
        )

        style = Style.from_dict(
            {
                "title": "bold",
                "model-list": "",
                "model-list-container": "",
                "model-list.current": "fg:cyan",
                "model-list.selected": "reverse",
                "model-list.selected-current": "reverse fg:cyan",
                "model-list.empty": "italic #888888",
                "search.prompt": "fg:#888888",
                "search.input": "",
                "footer": "fg:#888888",
            }
        )

        app: Optional[Application] = Application(
            layout=Layout(container, focused_element=list_window),
            key_bindings=kb,
            full_screen=True,
            style=style,
        )

        # Run the popup and react to the result.
        chosen_model = app.run()
        if chosen_model:
            self.model_manager.set_model(chosen_model)
            self._print_status("Ready")


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M")


def run_cli(
    *,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[int] = None,
    plain_output: bool = False,
    full_screen: Optional[bool] = None,
) -> int:
    # Allow configuring OPENROUTER_API_KEY (and other settings) via a local .env file.
    load_dotenv()
    try:
        app = ChatApp(
            initial_model=model,
            api_key=api_key,
            timeout=timeout,
            plain_output=plain_output,
            full_screen=full_screen,
        )
    except (MissingAPIKeyError, ValueError) as exc:
        _print_startup_error(str(exc), plain_output)
        return 1

    try:
        app.run()
    except MissingAPIKeyError:
        # Already surfaced to the user in context; exit with a non-zero status.
        return 1
    return 0


def _print_startup_error(message: str, plain_output: bool) -> None:
    console = _create_console(plain_output)
    if plain_output:
        console.print(f"Error: {message}")
    else:
        console.print(f"[bold red]{message}[/bold red]")


def _create_console(plain_output: bool) -> Console:
    if plain_output:
        return Console(
            markup=False,
            highlight=False,
            emoji=False,
            force_terminal=False,
            color_system=None,
            soft_wrap=True,
        )
    return Console(soft_wrap=True)
