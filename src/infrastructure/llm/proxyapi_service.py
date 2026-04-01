"""ProxyAPI-backed LLM service for the migrated interface layer."""

from __future__ import annotations

import time
from typing import Iterable
from uuid import UUID

from openai import APIStatusError, APITimeoutError, AsyncOpenAI

from src.application.llm import LLMCompletionOutput
from src.core.config import Settings
from src.domain.llm import LLMLogRepository, LLMModel, LLMRequestType, LLMResponse, LLMService, LLMPrompt

PROXYAPI_BASE_URL = "https://api.proxyapi.ru/openai/v1"

_SYSTEM_FACT = (
    "Ты — помощник в образовательной игре о генетике MyGenetics. "
    "Отвечай коротко (3–5 предложений), интересно и без технического жаргона. "
    "Пиши на русском языке."
)

_SYSTEM_CHAT = (
    "Ты — дружелюбный эксперт по генетике в Telegram-боте MyGenetics. "
    "Отвечай понятно, без лишнего жаргона, используй аналогии из жизни. "
    "Максимум 5–7 предложений на ответ. Пиши на русском языке. "
    "Если вопрос не связан с генетикой или биологией — вежливо перенаправь к теме."
)

_FALLBACK = "😔 Не удалось получить ответ от ИИ. Попробуйте чуть позже."


class ProxyApiLLMService:
    """Generate LLM responses through ProxyAPI and persist logs through the repository."""

    def __init__(self, settings: Settings, llm_log_repository: LLMLogRepository):
        self._settings = settings
        self._llm_log_repository = llm_log_repository
        self._client = AsyncOpenAI(
            api_key=settings.proxyapi_key,
            base_url=PROXYAPI_BASE_URL,
            timeout=20.0,
        )

    async def generate_gene_fact(
        self,
        gene_name: str,
        gene_description: str,
        user_id: UUID | None = None,
    ) -> LLMCompletionOutput:
        """Generate one short genetics fact."""
        prompt = (
            f"Расскажи один интересный и неочевидный факт о гене {gene_name}. "
            f"Контекст: {gene_description}. "
            "Факт должен удивить обычного человека без медицинского образования."
        )
        return await self._complete(
            request_type=LLMRequestType.FACT,
            prompt=prompt,
            user_id=user_id,
            messages=[
                {"role": "system", "content": _SYSTEM_FACT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=300,
        )

    async def answer_genetics_question(
        self,
        question: str,
        history: Iterable[tuple[str, str]],
        user_id: UUID | None = None,
    ) -> LLMCompletionOutput:
        """Answer a genetics question with optional short conversation history."""
        messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_CHAT}]
        for role, text in history:
            messages.append({"role": role, "content": text})
        messages.append({"role": "user", "content": question})

        return await self._complete(
            request_type=LLMRequestType.CHAT,
            prompt=question,
            user_id=user_id,
            messages=messages,
            temperature=0.6,
            max_tokens=500,
        )

    async def _complete(
        self,
        request_type: LLMRequestType,
        prompt: str,
        user_id: UUID | None,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMCompletionOutput:
        response_text = _FALLBACK
        is_fallback = False
        error_text: str | None = None
        started_at = time.monotonic()

        try:
            completion = await self._client.chat.completions.create(
                model=self._settings.proxyapi_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response_text = completion.choices[0].message.content or _FALLBACK
        except APITimeoutError:
            is_fallback = True
            error_text = "timeout"
        except APIStatusError as error:
            is_fallback = True
            error_text = f"HTTP {error.status_code}: {str(error.message)[:200]}"
        except Exception as error:
            is_fallback = True
            error_text = str(error)[:255]

        latency_ms = int((time.monotonic() - started_at) * 1000)
        if is_fallback:
            response_text = _FALLBACK

        await self._save_log(
            request_type=request_type,
            prompt=prompt,
            response_text=response_text,
            is_fallback=is_fallback,
            latency_ms=latency_ms,
            user_id=user_id,
            error_text=error_text,
        )

        return LLMCompletionOutput(
            text=response_text,
            is_fallback=is_fallback,
            latency_ms=latency_ms,
        )

    async def _save_log(
        self,
        request_type: LLMRequestType,
        prompt: str,
        response_text: str,
        is_fallback: bool,
        latency_ms: int,
        user_id: UUID | None,
        error_text: str | None,
    ) -> None:
        """Persist a log entry without changing request behavior if logging fails."""
        try:
            log_entry = LLMService.create_log_entry(
                request_type=request_type,
                model=_resolve_model(self._settings.proxyapi_model),
                prompt=LLMPrompt(prompt),
                response=LLMResponse(response_text, is_fallback=is_fallback),
                latency_ms=latency_ms,
                user_id=user_id,
                error=error_text,
            )
            await self._llm_log_repository.save(log_entry)
        except Exception:
            return


def _resolve_model(model_name: str) -> LLMModel:
    """Map configured model strings to the domain enum."""
    try:
        return LLMModel(model_name)
    except ValueError:
        return LLMModel.PROXYAPI