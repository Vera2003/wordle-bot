"""LLM domain value objects."""

from __future__ import annotations

from enum import Enum


class LLMRequestType(str, Enum):
    """Types of requests to LLM API."""
    
    FACT = "fact"  # Request for extracting facts from text
    CHAT = "chat"  # Chat conversation request


class LLMModel(str, Enum):
    """Supported LLM models."""
    
    YANDEX_GPT = "yandex_gpt"
    # Can extend with other models (OpenAI, Claude, etc.)


class LLMPrompt:
    """
    Value Object: The prompt sent to LLM.
    
    Contains the actual text/instruction sent to the model.
    """
    
    def __init__(self, text: str):
        if not text or not isinstance(text, str):
            raise ValueError("Prompt text must be non-empty string")
        
        if len(text) > 10000:  # Reasonable limit
            raise ValueError("Prompt cannot exceed 10000 characters")
        
        self._text = text.strip()
    
    @property
    def text(self) -> str:
        return self._text
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LLMPrompt):
            return False
        return self._text == other._text
    
    def __hash__(self) -> int:
        return hash(self._text)
    
    def __repr__(self) -> str:
        preview = self._text[:50] + "..." if len(self._text) > 50 else self._text
        return f"LLMPrompt(text={preview!r})"


class LLMResponse:
    """
    Value Object: The response from LLM API.
    
    Can be None if request failed and fallback was used.
    """
    
    def __init__(self, text: str | None = None, is_fallback: bool = False):
        if text is not None:
            if not isinstance(text, str):
                raise ValueError("Response text must be string or None")
            
            if len(text) > 50000:  # Reasonable limit
                raise ValueError("Response cannot exceed 50000 characters")
            
            self._text = text.strip() if text else None
        else:
            self._text = None
        
        self._is_fallback = is_fallback
    
    @property
    def text(self) -> str | None:
        return self._text
    
    @property
    def is_fallback(self) -> bool:
        """Whether this is a fallback response (error case)."""
        return self._is_fallback
    
    @property
    def is_successful(self) -> bool:
        """Whether we got a real response (not fallback)."""
        return self._text is not None and not self._is_fallback
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LLMResponse):
            return False
        return (
            self._text == other._text
            and self._is_fallback == other._is_fallback
        )
    
    def __hash__(self) -> int:
        return hash((self._text, self._is_fallback))
    
    def __repr__(self) -> str:
        status = "fallback" if self._is_fallback else "success"
        preview = (
            self._text[:50] + "..." if self._text and len(self._text) > 50
            else self._text
        )
        return f"LLMResponse(status={status}, text={preview!r})"


class LLMLatency:
    """
    Value Object: Response time in milliseconds.
    
    Used for monitoring and tracking API performance.
    """
    
    # Threshold for "slow" responses (ms)
    SLOW_THRESHOLD_MS = 3000
    
    def __init__(self, milliseconds: int | None):
        if milliseconds is not None:
            if not isinstance(milliseconds, int) or milliseconds < 0:
                raise ValueError("Latency must be non-negative integer (ms)")
        
        self._milliseconds = milliseconds
    
    @property
    def milliseconds(self) -> int | None:
        return self._milliseconds
    
    def is_slow(self) -> bool:
        """Check if response was slower than threshold."""
        if self._milliseconds is None:
            return False
        return self._milliseconds > self.SLOW_THRESHOLD_MS
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LLMLatency):
            return False
        return self._milliseconds == other._milliseconds
    
    def __hash__(self) -> int:
        return hash(self._milliseconds)
    
    def __repr__(self) -> str:
        if self._milliseconds is None:
            return "LLMLatency(unknown)"
        return f"LLMLatency(ms={self._milliseconds})"
