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
        return self._client.create(**kwargs)


class _FakeChat:
    def __init__(self, client: FakeClient) -> None:
        self.completions = _FakeCompletions(client)


class FakeClient:
    """Mimics ``client.chat.completions.create()`` and records every call."""

    def __init__(self, response_content: str) -> None:
        self.response_content = response_content
        self.calls: list[dict[str, Any]] = []
        self.chat = _FakeChat(self)

    def create(self, **kwargs: Any) -> _FakeResponse:
        """The seam a subclass overrides to reject a parameter or script a sequence."""
        self.calls.append(kwargs)
        return _FakeResponse(self.response_content)
