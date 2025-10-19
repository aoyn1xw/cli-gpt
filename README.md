# cli-gpt

Terminal chat interface for the OpenRouter free model tier.

## Features

- Works with predefined free OpenRouter models.
- Automatically refreshes the free model catalogue from OpenRouter at startup (falls back to bundled list when offline).
- Persists conversation context with a safety system prompt.
- Slash commands for listing and switching models, clearing history, and exiting.
- Terminal UI with coloured chat log and status panel.
- Shows a live typing indicator while the assistant generates responses.
- Launches in full-screen mode for an immersive terminal experience (disable with `--no-fullscreen`).
- `/list` opens a scrollable popup (falls back to plain output when a pager isn't available).

## Installation

### With pip (recommended)

```bash
pip install cli-gpt
```

### With pipx

```bash
pipx install cli-gpt
```

### From a local checkout

```bash
pip install .
# or
pipx install .
```

## Usage

Copy `.env.example` to `.env`, fill in your personal `OPENROUTER_API_KEY` (never commit or share it), or export the variable in your shell. Then run:

```bash
cli-gpt
```

### CLI options

- `--list-models` – show available models and exit.
- `--model <name>` – start the session on a specific model.
- `--plain` – disable rich formatting (useful for minimal terminals).
- `--timeout <seconds>` – override the default 45 second request timeout.
- `--api-key <value>` – provide the API key directly without setting an env var.
- `--fullscreen` / `--no-fullscreen` – force or disable full-screen terminal mode.
- `--version` – print the application version and exit.

### Commands

- `/list` – list available models.
- `/model <name>` – switch to another free model.
- `/clear` – clear chat history (system prompt is kept).
- `/help` – show supported commands.
- `/quit` or `/exit` – leave the application.

If the assistant replies with `I need to check the web for this.`, the app reminds you that web search is not part of the free mode yet.
