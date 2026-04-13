# cli-gpt

Terminal chat interface for OpenRouter free-tier models.

## Features

- Live free-model refresh from OpenRouter on startup and whenever `/list` is opened, with a bundled fallback list if the API is unavailable.
- Interactive model selector with arrow-key navigation, search-as-you-type filtering, and enter-to-select; `/list` downgrades gracefully to plain text when colors/TTY are unavailable.
- Persists the system prompt and conversation history until you clear it, so multi-turn chats remain coherent.
- Rich terminal presentation: banner, status panel, colored chat log, typing indicator while replies stream, and optional full-screen layout (toggle with `--no-fullscreen`).
- Slash commands for model management, help, clearing history, and quick exits.
- Ships with a `.env.example` for safe API key management and supports override variables (`OPENROUTER_API_URL`, `OPENROUTER_MODELS_URL`, etc.).

## Installation

### From a local checkout

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Publishing to PyPI/pipx is coming soon. In the meantime you can build distributables locally (see below) and install them with `pipx install dist/cli_gpt-*.whl`.

## Setup & Usage

1. Copy the example environment file and add your OpenRouter key:
   ```bash
   cp .env.example .env
   echo 'OPENROUTER_API_KEY=your-key-here' >> .env
   ```
2. Launch the app:
   ```bash
   cli-gpt
   ```

The models listed in the selector are sourced live from the OpenRouter API when a key is available. There is currently no web browsing capability; when a model cannot answer it will explicitly state so rather than fabricating information.

### CLI options

- `--list-models` - print the available free models and exit (uses live data when possible).
- `--model <name>` - start on a specific model from the free tier.
- `--plain` - disable Rich formatting for minimal output.
- `--timeout <seconds>` - override the 45 second request timeout.
- `--api-key <value>` - provide an API key without using environment variables.
- `--fullscreen` / `--no-fullscreen` - force or disable full-screen mode.
- `--version` - print the application version and exit.

### Commands inside the app

- `/list` - open the interactive model selector.
- `/model <name>` - switch directly to another free model.
- `/clear` - clear chat history (retains the system prompt).
- `/help` - show available commands.
- `/quit` or `/exit` - leave the application.

## Building distributables (for pip/pipx)

```bash
source .venv/bin/activate
python -m build
```

This produces `dist/cli_gpt-<version>.tar.gz` and the matching wheel. Test installation with:

```bash
pipx install dist/cli_gpt-<version>-py3-none-any.whl
```

Publish with `python -m twine upload dist/*` once you are ready.

## Contributing

Fork the repository, make your changes on a branch, and open a pull request. Please keep secrets out of commits (`.env` is ignored by default) and run `pip install -e .` to ensure the CLI still boots before submitting. Suggestions, bug reports, and feature ideas are all welcome!
