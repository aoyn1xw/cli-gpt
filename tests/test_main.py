from cli_gpt import __main__ as cli_main
from cli_gpt.models import FREE_MODELS


class FakeClient:
    def __init__(self, api_key, timeout):
        self.api_key = api_key
        self.timeout = timeout

    def list_models(self, free_only=True):
        assert free_only is True
        return ["live/model-a", "live/model-b"]


def test_list_models_uses_bundled_fallback_without_api_key(capsys):
    exit_code = cli_main.main(["--list-models"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Using bundled free model list" in captured.out
    for model in FREE_MODELS:
        assert model in captured.out


def test_list_models_uses_live_catalog_when_api_key_present(monkeypatch, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(cli_main, "OpenRouterClient", FakeClient)

    exit_code = cli_main.main(["--list-models", "--timeout", "12"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Using bundled free model list" not in captured.out
    assert captured.out.splitlines() == ["live/model-a", "live/model-b"]
