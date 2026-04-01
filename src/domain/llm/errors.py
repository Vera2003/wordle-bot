"""LLM domain errors."""


class LLMError(Exception):
    """Base exception for LLM domain."""

    pass


class LLMRequestTypeInvalidError(LLMError):
    """Request type is not a valid type (should be: fact | chat)."""

    pass


class LLMResponseError(LLMError):
    """Error in LLM response or API call."""

    pass


class LLMLatencyError(LLMError):
    """LLM response latency exceeds acceptable threshold."""

    pass
