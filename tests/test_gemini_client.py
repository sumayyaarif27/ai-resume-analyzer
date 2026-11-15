"""Tests for src/gemini_client.py and src/config.py.

A fake client replaces the real Gemini client, so these tests need no
internet and no API key. The waiting time between retries is skipped too.
"""

from types import SimpleNamespace

import pytest
from google.genai import errors

from src import config, gemini_client
from src.gemini_client import GeminiAPIError, ask_gemini_json

GOOD_REPLY = SimpleNamespace(text='{"ok": true}')


class FakeClient:
    """Stands in for the Gemini client and plays back prepared outcomes."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.models = self  # so client.models.generate_content(...) works

    def generate_content(self, model, contents, config=None):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def make_error(code):
    """Build an API error like the ones Gemini sends back."""
    body = {"error": {"message": "test error", "status": "TEST"}}
    error_class = errors.ServerError if code >= 500 else errors.ClientError
    return error_class(code, body)


def use_fake_client(monkeypatch, outcomes):
    """Install the fake client. Returns it, plus a list of 'sleep' waits."""
    client = FakeClient(outcomes)
    waits = []
    monkeypatch.setattr(gemini_client, "get_client", lambda: client)
    monkeypatch.setattr(gemini_client.time, "sleep", waits.append)
    return client, waits


# ---------- Success and retries ----------

def test_first_try_success(monkeypatch):
    client, waits = use_fake_client(monkeypatch, [GOOD_REPLY])
    assert ask_gemini_json("hello") == '{"ok": true}'
    assert client.calls == 1
    assert waits == []


def test_rate_limit_then_success_retries(monkeypatch):
    client, waits = use_fake_client(monkeypatch, [make_error(429), GOOD_REPLY])
    assert ask_gemini_json("hello") == '{"ok": true}'
    assert client.calls == 2
    assert waits == [5]


def test_rate_limit_every_time_gives_clear_message(monkeypatch):
    client, waits = use_fake_client(
        monkeypatch, [make_error(429), make_error(429), make_error(429)]
    )
    with pytest.raises(GeminiAPIError, match="Rate limit"):
        ask_gemini_json("hello")
    assert client.calls == 3      # 1 try + 2 retries
    assert waits == [5, 10]       # waits a little longer each time


def test_server_busy_every_time_gives_clear_message(monkeypatch):
    client, _ = use_fake_client(
        monkeypatch, [make_error(503), make_error(503), make_error(503)]
    )
    with pytest.raises(GeminiAPIError, match="busy"):
        ask_gemini_json("hello")
    assert client.calls == 3


# ---------- Errors that must NOT be retried ----------

@pytest.mark.parametrize(
    "code, message",
    [(401, "API key"), (403, "API key"), (404, "Model not found")],
)
def test_permanent_errors_are_not_retried(monkeypatch, code, message):
    client, waits = use_fake_client(monkeypatch, [make_error(code)])
    with pytest.raises(GeminiAPIError, match=message):
        ask_gemini_json("hello")
    assert client.calls == 1      # retrying would not help
    assert waits == []


def test_unknown_error_code_is_reported(monkeypatch):
    use_fake_client(monkeypatch, [make_error(418)])
    with pytest.raises(GeminiAPIError, match="code 418"):
        ask_gemini_json("hello")


# ---------- Other failures ----------

def test_no_internet_gives_clear_message(monkeypatch):
    client, _ = use_fake_client(monkeypatch, [ConnectionError("no internet")])
    with pytest.raises(GeminiAPIError, match="internet"):
        ask_gemini_json("hello")
    assert client.calls == 1


def test_empty_reply_is_rejected(monkeypatch):
    client, _ = use_fake_client(monkeypatch, [SimpleNamespace(text="")])
    with pytest.raises(GeminiAPIError, match="empty"):
        ask_gemini_json("hello")
    assert client.calls == 1


# ---------- Configuration ----------

def test_missing_api_key_gives_clear_error(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    with pytest.raises(ValueError, match="GEMINI_API_KEY not found"):
        config.validate_config()