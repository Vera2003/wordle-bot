from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class LLMLog(Base):
    """
    Лог каждого обращения к YandexGPT.

    Используется для оценки качества ответов, мониторинга затрат
    и отладки промптов.
    """

    __tablename__ = "llm_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Кто и когда
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True,
        comment="ID пользователя из таблицы users (NULL для API-запросов)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    # Тип запроса
    request_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="fact | chat",
    )

    # Входные данные
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)

    # Выходные данные
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_fallback: Mapped[bool] = mapped_column(
        default=False,
        comment="True если вернули заглушку из-за ошибки",
    )

    # Метрики
    latency_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Время ответа API в миллисекундах",
    )
    error: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Текст ошибки если запрос не удался",
    )

    def __repr__(self) -> str:
        return (
            f"<LLMLog(id={self.id}, type={self.request_type}, "
            f"user_id={self.user_id}, fallback={self.is_fallback})>"
        )