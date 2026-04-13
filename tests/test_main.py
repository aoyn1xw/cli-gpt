from cli_gpt import __main__ as cli_main
from cli_gpt.models import FREE_MODELS


def test_list_models_uses_bundled_fallback_on_fetch_error(monkeypatch, capsys):
    def fake_fetch_models_catalogue(*, api_key, timeout, free_only):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli_main, "fetch_models_catalogue", fake_fetch_models_catalogue)
    exit_code = cli_main.main(["--list-models"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines() == FREE_MODELS


def test_list_models_uses_live_catalog_when_fetch_succeeds(monkeypatch, capsys):
    def fake_fetch_models_catalogue(*, api_key, timeout, free_only):
        assert api_key is None
        assert timeout == 12
        assert free_only is True
        return ["live/model-a", "live/model-b"]

    monkeypatch.setattr(cli_main, "fetch_models_catalogue", fake_fetch_models_catalogue)

    exit_code = cli_main.main(["--list-models", "--timeout", "12"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines() == ["live/model-a", "live/model-b"]
