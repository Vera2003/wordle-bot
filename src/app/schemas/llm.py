from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# POST /api/v1/llm/fact
# ---------------------------------------------------------------------------


class GeneFactRequest(BaseModel):
    """Тело запроса для генерации факта о гене."""

    gene_name: str = Field(
        ...,
        min_length=3,
        max_length=10,
        description="Название гена",
        examples=["MTHFR", "TCF7L2"],
    )
    gene_description: str = Field(
        ...,
        min_length=20,
        description="Описание гена из базы данных",
    )


class GeneFactResponse(BaseModel):
    """Ответ с интересным фактом о гене."""

    gene_name: str
    fact: str = Field(..., description="Сгенерированный факт от YandexGPT")
    is_fallback: bool = Field(
        ..., description="True если LLM недоступна и вернули заглушку"
    )
    latency_ms: int = Field(..., description="Время генерации в миллисекундах")


# ---------------------------------------------------------------------------
# POST /api/v1/llm/chat
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """Одно сообщение в истории диалога."""

    role: str = Field(
        ...,
        pattern="^(user|assistant)$",
        description="Роль отправителя: user или assistant",
    )
    text: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    """Тело запроса для вопроса о генетике."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Вопрос пользователя",
        examples=["Что такое ген?", "Как работает CRISPR?"],
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="История предыдущих сообщений (максимум 10)",
        max_length=10,
    )


class ChatResponse(BaseModel):
    """Ответ на вопрос о генетике."""

    question: str
    answer: str = Field(..., description="Ответ YandexGPT")
    is_fallback: bool = Field(
        ..., description="True если LLM недоступна и вернули заглушку"
    )
    latency_ms: int = Field(..., description="Время генерации в миллисекундах")


# ---------------------------------------------------------------------------
# GET /api/v1/llm/logs — просмотр логов (только для админа)
# ---------------------------------------------------------------------------


class LLMLogResponse(BaseModel):
    """Один лог-запись для просмотра в админке."""

    id: int
    user_id: Optional[int]
    request_type: str
    model: str
    prompt: str
    response: Optional[str]
    is_fallback: bool
    latency_ms: Optional[int]
    error: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class LLMLogListResponse(BaseModel):
    """Постраничный список логов."""

    total: int
    items: list[LLMLogResponse]


class LLMStatsResponse(BaseModel):
    """Агрегированная статистика по логам — для оценки качества."""

    total_requests: int = Field(..., description="Всего запросов")
    fallback_count: int = Field(..., description="Из них вернули заглушку")
    fallback_rate: float = Field(..., description="Процент заглушек (0–100)")
    avg_latency_ms: Optional[float] = Field(..., description="Среднее время ответа")
    requests_by_type: dict[str, int] = Field(
        ..., description="Количество запросов по типу: {'fact': 120, 'chat': 45}"
    )