"""
Сервис интеграции с LLM через ProxyAPI (https://proxyapi.ru).

ProxyAPI — российский прокси к OpenAI. Использует стандартный openai-клиент
с кастомным base_url, поэтому API идентично официальному OpenAI SDK.

Каждый запрос логируется в таблицу llm_logs для мониторинга качества.
"""
import asyncio
import time
from typing import Literal

import structlog
from openai import AsyncOpenAI, APIStatusError, APITimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..db.models.llm_log import LLMLog

logger = structlog.get_logger(__name__)

PROXYAPI_BASE_URL = "https://api.proxyapi.ru/openai/v1"

RequestType = Literal["fact", "chat"]

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


class LLMService:
    """
    Клиент ProxyAPI с логированием каждого запроса в БД.

    Пример использования:
        llm = LLMService(db=db, user_id=user.id)
        fact, is_fallback, latency_ms = await llm.get_gene_fact("MTHFR", "...")
        answer, is_fallback, latency_ms = await llm.answer_genetics_question("Что такое ген?")
    """

    def __init__(
        self,
        db: AsyncSession | None = None,
        user_id: int | None = None,
    ) -> None:
        """
        Args:
            db: Сессия БД для логирования. Если None — логи не сохраняются.
            user_id: ID пользователя из таблицы users (для привязки лога).
        """
        self._settings = get_settings()
        self._db = db
        self._user_id = user_id
        self._client = AsyncOpenAI(
            api_key=self._settings.proxyapi_key,
            base_url=PROXYAPI_BASE_URL,
            timeout=20.0,
        )

    async def _complete(
        self,
        messages: list[dict],
        request_type: RequestType,
        prompt_for_log: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> tuple[str, bool, int]:
        """
        Базовый вызов API.

        Returns:
            (текст_ответа, is_fallback, latency_ms)
        """
        response_text = _FALLBACK
        is_fallback = False
        error_text: str | None = None
        start = time.monotonic()

        try:
            completion = await self._client.chat.completions.create(
                model=self._settings.proxyapi_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response_text = completion.choices[0].message.content or _FALLBACK

        except APITimeoutError:
            error_text = "timeout"
            is_fallback = True
            logger.warning("ProxyAPI timeout")

        except APIStatusError as e:
            error_text = f"HTTP {e.status_code}: {str(e.message)[:200]}"
            is_fallback = True
            logger.error("ProxyAPI status error", status=e.status_code, message=e.message)

        except Exception as e:
            error_text = str(e)[:255]
            is_fallback = True
            logger.error("ProxyAPI unexpected error", error=str(e))

        latency_ms = int((time.monotonic() - start) * 1000)

        if is_fallback:
            response_text = _FALLBACK

        await self._save_log(
            request_type=request_type,
            prompt=prompt_for_log,
            response=response_text,
            is_fallback=is_fallback,
            latency_ms=latency_ms,
            error=error_text,
        )

        return response_text, is_fallback, latency_ms

    async def _save_log(
        self,
        request_type: RequestType,
        prompt: str,
        response: str,
        is_fallback: bool,
        latency_ms: int,
        error: str | None,
    ) -> None:
        """Сохранить запись в llm_logs. Ошибки логирования не роняют основной поток."""
        if not self._db:
            return
        try:
            self._db.add(LLMLog(
                user_id=self._user_id,
                request_type=request_type,
                model=self._settings.proxyapi_model,
                prompt=prompt,
                response=response,
                is_fallback=is_fallback,
                latency_ms=latency_ms,
                error=error,
            ))
            await self._db.commit()
        except Exception as e:
            logger.error("Failed to save LLM log", error=str(e))

    async def get_gene_fact(
        self,
        gene_name: str,
        gene_description: str,
    ) -> tuple[str, bool, int]:
        """
        Сгенерировать интересный факт о гене.

        Returns:
            (факт, is_fallback, latency_ms)
        """
        prompt = (
            f"Расскажи один интересный и неочевидный факт о гене {gene_name}. "
            f"Контекст: {gene_description}. "
            f"Факт должен удивить обычного человека без медицинского образования."
        )
        return await self._complete(
            messages=[
                {"role": "system", "content": _SYSTEM_FACT},
                {"role": "user", "content": prompt},
            ],
            request_type="fact",
            prompt_for_log=prompt,
            temperature=0.8,
            max_tokens=300,
        )

    async def answer_genetics_question(
        self,
        question: str,
        history: list[dict] | None = None,
    ) -> tuple[str, bool, int]:
        """
        Ответить на вопрос пользователя о генетике.

        Returns:
            (ответ, is_fallback, latency_ms)
        """
        messages: list[dict] = [{"role": "system", "content": _SYSTEM_CHAT}]

        for msg in (history or [])[-6:]:
            # история из FSM хранит ключ "text", OpenAI ждёт "content"
            messages.append({"role": msg["role"], "content": msg["text"]})

        messages.append({"role": "user", "content": question})

        return await self._complete(
            messages=messages,
            request_type="chat",
            prompt_for_log=question,
            temperature=0.6,
            max_tokens=500,
        )