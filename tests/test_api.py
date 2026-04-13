from cli_gpt.api import (
    OpenRouterClient,
    get_api_url,
    get_app_referer,
    get_app_title,
    get_models_url,
)


class DummyResponse:
    def __init__(self, payload, ok=True, status_code=200):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload


class DummySession:
    def __init__(self, response):
        self.response = response
        self.last_get = None

    def get(self, url, headers, timeout):
        self.last_get = {"url": url, "headers": headers, "timeout": timeout}
        return self.response


def test_runtime_env_configuration_is_resolved_per_call(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_URL", "https://example.test/chat")
    monkeypatch.setenv("OPENROUTER_MODELS_URL", "https://example.test/models")
    monkeypatch.setenv("CLI_GPT_APP_TITLE", "cli-gpt-test")
    monkeypatch.setenv("CLI_GPT_APP_REFERER", "https://example.test/app")

    assert get_api_url() == "https://example.test/chat"
    assert get_models_url() == "https://example.test/models"
    assert get_app_title() == "cli-gpt-test"
    assert get_app_referer() == "https://example.test/app"


def test_list_models_uses_runtime_env_values_and_filters_free_models(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODELS_URL", "https://example.test/models")
    monkeypatch.setenv("CLI_GPT_APP_TITLE", "cli-gpt-test")
    monkeypatch.setenv("CLI_GPT_APP_REFERER", "https://example.test/app")
    session = DummySession(
        DummyResponse(
            {
                "data": [
                    {
                        "id": "free/model-one",
                        "pricing": {"prompt": "0", "completion": "0.0"},
                    },
                    {
                        "id": "paid/model-two",
                        "pricing": {"prompt": "1", "completion": "0"},
                    },
                    {
                        "id": "free/model-one",
                        "pricing": {"prompt": "0", "completion": "0"},
                    },
                ]
            }
        )
    )

    client = OpenRouterClient(api_key="test-key", session=session)

    assert client.list_models() == ["free/model-one"]
    assert session.last_get == {
        "url": "https://example.test/models",
        "headers": {
            "Authorization": "Bearer test-key",
            "HTTP-Referer": "https://example.test/app",
            "X-Title": "cli-gpt-test",
        },
        "timeout": 45,
    }
