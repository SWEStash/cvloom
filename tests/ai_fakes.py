"""Fake OpenAI-compatible client for testing AI orchestration without a backend."""

from __future__ import annotations

from typing import Any


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, client: FakeClient) -> None:
        self._client = client

    def create(self, **kwargs: Any) -> _FakeResponse:
        self._client.calls.append(kwargs)
        return _FakeResponse(self._client.response_content)


class _FakeChat:
    def __init__(self, client: FakeClient) -> None:
        self.completions = _FakeCompletions(client)


class FakeClient:
    """Mimics ``client.chat.completions.create()`` and records every call."""

    def __init__(self, response_content: str) -> None:
        self.response_content = response_content
        self.calls: list[dict[str, Any]] = []
        self.chat = _FakeChat(self)
