"""Optional AI-powered analysis features for cvloom.

Requires the [ai] optional dependency group:
    uv sync --extra ai

All features are gated behind is_configured(). If no AI provider is
configured, existing cvloom commands are completely unaffected.
"""

from __future__ import annotations

from cvloom.ai.provider import AINotConfiguredError, get_client, get_model, is_configured

__all__ = ["AINotConfiguredError", "get_client", "get_model", "is_configured"]
