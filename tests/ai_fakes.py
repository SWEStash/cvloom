"""Fake OpenAI-compatible client for testing AI orchestration without a backend."""

from __future__ import annotations

from typing import Any


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeUsage:
    def __init__(self, prompt_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens


class _FakeResponse:
    def __init__(self, content: str, prompt_tokens: int | None = None) -> None:
        self.choices = [_FakeChoice(content)]
        # Set only when asked for, so `usage` stays genuinely absent by default —
        # that is what most OpenAI-compatible proxies do, and it is the path the
        # truncation check has to stay silent on.
        if prompt_tokens is not None:
            self.usage = _FakeUsage(prompt_tokens)


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

    def __init__(self, response_content: str, prompt_tokens: int | None = None) -> None:
        self.response_content = response_content
        self.prompt_tokens = prompt_tokens
        self.calls: list[dict[str, Any]] = []
        self.chat = _FakeChat(self)

    def create(self, **kwargs: Any) -> _FakeResponse:
        """The seam a subclass overrides to reject a parameter or script a sequence."""
        self.calls.append(kwargs)
        return _FakeResponse(self.response_content, self.prompt_tokens)


class FakeAPIStatusError(Exception):
    """An HTTP-shaped provider error, standing in for ``openai.BadRequestError``.

    The real one cannot be raised here: ``openai`` is an optional extra, and the
    provider deliberately never imports it at module scope. What the provider
    actually reads is ``status_code`` and the message text, both of which this has.
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class ScriptedClient(FakeClient):
    """Returns each response in turn, repeating the last once exhausted.

    Repeating rather than raising on over-call keeps a failure legible: a test that
    calls once too often fails on its own assertion, not on this fake's bookkeeping.
    """

    def __init__(self, *contents: str, prompt_tokens: int | None = None) -> None:
        super().__init__(contents[0], prompt_tokens)
        self._contents = list(contents)

    def create(self, **kwargs: Any) -> _FakeResponse:
        index = min(len(self.calls), len(self._contents) - 1)
        self.response_content = self._contents[index]
        return super().create(**kwargs)


class NoJsonModeClient(FakeClient):
    """Rejects any request carrying ``response_format``, as several backends do."""

    def __init__(self, response_content: str, *, error: Exception) -> None:
        super().__init__(response_content)
        self._error = error
        self.rejected = 0

    def create(self, **kwargs: Any) -> _FakeResponse:
        if "response_format" in kwargs:
            self.rejected += 1
            raise self._error
        return super().create(**kwargs)
