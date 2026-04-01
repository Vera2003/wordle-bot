"""Common application DTOs for shared concepts."""

from datetime import datetime
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")
ResultPayload = TypeVar("ResultPayload")


class BaseDTO(BaseModel):
    """Base DTO with strict model config."""

    model_config = ConfigDict(
        frozen=True,  # Immutable - нельзя менять после создания
        str_strip_whitespace=True,  # Убирать пробелы в строках
    )


class PaginationInput(BaseDTO):
    """Входные параметры для пагинации."""

    offset: int = Field(default=0, ge=0, description="Сколько элементов пропустить")
    limit: int = Field(
        default=20, ge=1, le=100, description="Сколько элементов вернуть"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Ответ с пагинацией."""

    items: list[T] = Field(..., description="Элементы страницы")
    total: int = Field(..., description="Всего элементов")
    offset: int = Field(..., description="Сколько пропустили")
    limit: int = Field(..., description="Размер страницы")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 100,
                "offset": 0,
                "limit": 20,
            }
        }
    )


class AuditMetadata(BaseDTO):
    """Метаинформация об объекте (создание, изменение)."""

    created_at: datetime = Field(..., description="Когда создано")
    updated_at: Optional[datetime] = Field(
        None, description="Когда последний раз изменено"
    )


class EntityId(BaseDTO):
    """ID сущности."""

    id: UUID = Field(..., description="Уникальный ID")


class OperationResult(BaseModel, Generic[ResultPayload]):
    """Результат операции (успех/ошибка)."""

    success: bool = Field(..., description="Успешно ли выполнено")
    message: Optional[str] = Field(None, description="Сообщение (обычно для ошибок)")
    data: Optional[ResultPayload] = Field(None, description="Дополнительные данные")

    model_config = ConfigDict(frozen=True)


# Ошибки приложения


class ApplicationError(Exception):
    """Базовая ошибка приложения."""

    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(message)


class ValidationError(ApplicationError):
    """Ошибка валидации входных данных."""

    pass


class NotFoundError(ApplicationError):
    """Сущность не найдена."""

    pass


class ConflictError(ApplicationError):
    """Конфликт (например, дублирование)."""

    pass


class UnauthorizedError(ApplicationError):
    """Не авторизирован."""

    pass


class ForbiddenError(ApplicationError):
    """Нет доступа."""

    pass
