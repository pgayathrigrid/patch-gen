"""
Mock LLM provider for unit testing.

``MockLlmProvider`` returns predictable, fully-structured JSON responses so
tests never make real network calls.  The response content can be customised
at construction time to test different scenarios (valid JSON, malformed JSON,
provider errors, etc.).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from awcp_instrumentation.application.generator.llm_interface import (
    LlmProvider,
    LlmProviderError,
    LlmRequest,
    LlmResponse,
)


# ---------------------------------------------------------------------------
# Default mock response
# ---------------------------------------------------------------------------

def _default_response_json(request: LlmRequest) -> str:
    """
    Build a deterministic, valid JSON response from the request content.

    The response is deliberately minimal and structurally correct so the
    ``ResponseParser`` can always parse it in the happy-path tests.
    """
    # Extract the AWCP lifecycle hook category from the prompt (best-effort).
    category = "task_started"
    for token in [
        "task_started", "task_completed", "task_failed",
        "llm_call", "tool_call", "web_search", "synthesize",
        "token_usage", "budget_warn", "budget_exhausted",
    ]:
        if token in request.prompt.lower():
            category = token
            break

    response: Dict[str, Any] = {
        "import_additions": ["import awcp_hooks"],
        "changes": [
            {
                "code_fragment": f"awcp_hooks.{category}(task_id, agent_name)",
                "location": "before_function_body",
                "target_function": "run",
                "explanation": (
                    f"Insert AWCP {category} lifecycle hook at the entry point "
                    "of the agent's main execution function."
                ),
            }
        ],
        "explanation": (
            f"Added awcp_hooks.{category}() to satisfy AWCP lifecycle instrumentation. "
            "The hook is placed at the agent's primary execution entry point."
        ),
        "confidence": 0.85,
    }
    return json.dumps(response, indent=2)


# ---------------------------------------------------------------------------
# MockLlmProvider
# ---------------------------------------------------------------------------

class MockLlmProvider(LlmProvider):
    """
    Deterministic LLM provider stub for unit and integration tests.

    Args:
        response_content:   The string to return as ``LlmResponse.content``.
                            When ``None``, a default valid JSON response is
                            generated from the request.
        model_name:         The model identifier reported in responses.
        prompt_tokens:      Simulated prompt token count.
        completion_tokens:  Simulated completion token count.
        raise_error:        When set, ``complete()`` raises this exception
                            instead of returning a response — used to test
                            failure handling paths.
        call_log:           Mutable list that records every ``LlmRequest``
                            passed to ``complete()``.  Inspect in tests to
                            verify prompt content without monkey-patching.
    """

    def __init__(
        self,
        response_content: Optional[str] = None,
        model_name: str = "mock-model-1.0",
        prompt_tokens: int = 120,
        completion_tokens: int = 80,
        raise_error: Optional[Exception] = None,
        call_log: Optional[List[LlmRequest]] = None,
    ) -> None:
        self._response_content = response_content
        self._model_name = model_name
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens
        self._raise_error = raise_error
        self._call_log: List[LlmRequest] = call_log if call_log is not None else []

    # ------------------------------------------------------------------
    # LlmProvider interface
    # ------------------------------------------------------------------

    def complete(self, request: LlmRequest) -> LlmResponse:
        self._call_log.append(request)

        if self._raise_error is not None:
            raise self._raise_error

        content = (
            self._response_content
            if self._response_content is not None
            else _default_response_json(request)
        )
        effective_model = request.model or self._model_name

        return LlmResponse(
            content=content,
            model=effective_model,
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            raw={"mock": True},
        )

    @property
    def default_model(self) -> str:
        return self._model_name

    @property
    def provider_name(self) -> str:
        return "MockLlmProvider"

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    @property
    def call_count(self) -> int:
        """Number of times ``complete()`` was called."""
        return len(self._call_log)

    @property
    def last_request(self) -> Optional[LlmRequest]:
        """The most recent ``LlmRequest`` passed to ``complete()``."""
        return self._call_log[-1] if self._call_log else None
