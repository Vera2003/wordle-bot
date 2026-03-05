from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.security import require_admin_api_key
from ...db.models.llm_log import LLMLog
from ...db.session import get_db
from ...schemas.llm import (
    ChatRequest,
    ChatResponse,
    GeneFactRequest,
    GeneFactResponse,
    LLMLogListResponse,
    LLMLogResponse,
    LLMStatsResponse,
)
from ...services.llm_service import LLMService
from ...core.config import get_settings

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /llm/fact — генерация факта (публичный, без API-ключа — вызывается ботом)
# ---------------------------------------------------------------------------

@router.post("/fact", response_model=GeneFactResponse)
async def generate_gene_fact(
    body: GeneFactRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Сгенерировать интересный факт о гене через LLM.

    Вызывается ботом после каждой завершённой игры.
    Результат логируется в таблицу llm_logs.
    """
    settings = get_settings()
    if not settings.llm_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM не настроена: укажите PROXYAPI_KEY в .env",
        )

    llm = LLMService(db=db)
    fact, is_fallback, latency_ms = await llm.get_gene_fact(
        body.gene_name, body.gene_description
    )

    return GeneFactResponse(
        gene_name=body.gene_name,
        fact=fact,
        is_fallback=is_fallback,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# POST /llm/chat — вопрос о генетике (публичный)
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat_genetics(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Задать вопрос о генетике через LLM.

    Поддерживает историю диалога (передайте предыдущие сообщения в history).
    Результат логируется в таблицу llm_logs.
    """
    settings = get_settings()
    if not settings.llm_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM не настроена: укажите PROXYAPI_KEY в .env",
        )

    history = [{"role": m.role, "text": m.text} for m in body.history]

    llm = LLMService(db=db)
    answer, is_fallback, latency_ms = await llm.answer_genetics_question(
        body.question, history
    )

    return ChatResponse(
        question=body.question,
        answer=answer,
        is_fallback=is_fallback,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# GET /llm/logs — просмотр логов (только для админа)
# ---------------------------------------------------------------------------

@router.get(
    "/logs",
    response_model=LLMLogListResponse,
    dependencies=[Depends(require_admin_api_key)],
)
async def get_llm_logs(
    skip: int = 0,
    limit: int = 100,
    request_type: str | None = None,
    fallback_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список логов запросов к LLM.

    Фильтры:
    - request_type: fact | chat
    - fallback_only: только запросы где LLM вернула заглушку
    """
    query = select(LLMLog).order_by(LLMLog.created_at.desc())

    if request_type:
        query = query.where(LLMLog.request_type == request_type)
    if fallback_only:
        query = query.where(LLMLog.is_fallback == True)

    total: int = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    result = await db.execute(query.offset(skip).limit(limit))
    logs = result.scalars().all()

    return LLMLogListResponse(
        total=total,
        items=[LLMLogResponse.model_validate(log) for log in logs],
    )


# ---------------------------------------------------------------------------
# GET /llm/stats — агрегированная статистика (только для админа)
# ---------------------------------------------------------------------------

@router.get(
    "/stats",
    response_model=LLMStatsResponse,
    dependencies=[Depends(require_admin_api_key)],
)
async def get_llm_stats(db: AsyncSession = Depends(get_db)):
    """
    Агрегированная статистика качества LLM.

    Показывает: процент заглушек, среднее время ответа, разбивку по типам.
    """
    total: int = await db.scalar(select(func.count(LLMLog.id))) or 0
    fallback_count: int = await db.scalar(
        select(func.count(LLMLog.id)).where(LLMLog.is_fallback == True)
    ) or 0
    avg_latency = await db.scalar(
        select(func.avg(LLMLog.latency_ms)).where(LLMLog.latency_ms.is_not(None))
    )

    # Разбивка по типам запросов
    type_rows = await db.execute(
        select(LLMLog.request_type, func.count(LLMLog.id))
        .group_by(LLMLog.request_type)
    )
    requests_by_type = {row[0]: row[1] for row in type_rows.all()}

    return LLMStatsResponse(
        total_requests=total,
        fallback_count=fallback_count,
        fallback_rate=round(fallback_count / total * 100, 2) if total else 0.0,
        avg_latency_ms=round(avg_latency, 1) if avg_latency else None,
        requests_by_type=requests_by_type,
    )