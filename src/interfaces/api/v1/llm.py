"""LLM API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.llm import (
    AskGeneticsQuestionCommand,
    AskGeneticsQuestionHandler,
    ChatAnswerOutput,
    GeneFactOutput,
    GenerateGeneFactCommand,
    GenerateGeneFactHandler,
    GetLLMLogsHandler,
    GetLLMLogsQuery,
    GetLLMStatsHandler,
    GetLLMStatsQuery,
    LLMGenerationService,
    LLMLogListOutput,
    LLMStatsOutput,
)
from src.domain.llm import LLMRequestType
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.repositories.llm import LLMLogRepositoryImpl
from src.infrastructure.db.session import get_db_session
from src.infrastructure.llm import ProxyApiLLMService
from src.interfaces.api.security import require_admin_api_key

router = APIRouter(prefix="/llm", tags=["llm"])


async def get_llm_log_repository(
    db: AsyncSession = Depends(get_db_session),
) -> LLMLogRepositoryImpl:
    """Dependency: get llm log repository."""
    return LLMLogRepositoryImpl(db)


async def get_llm_service(
    repository: LLMLogRepositoryImpl = Depends(get_llm_log_repository),
    settings: Settings = Depends(get_settings),
) -> LLMGenerationService:
    """Dependency: get llm generation service."""
    return ProxyApiLLMService(settings=settings, llm_log_repository=repository)


@router.post("/fact")
async def generate_gene_fact(
    command: GenerateGeneFactCommand,
    service: LLMGenerationService = Depends(get_llm_service),
    settings: Settings = Depends(get_settings),
) -> GeneFactOutput:
    """Generate one short gene fact through the migrated interface layer."""
    if not settings.llm_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not configured: set PROXYAPI_KEY in the environment",
        )

    handler = GenerateGeneFactHandler(service)
    return await handler(command)


@router.post("/chat")
async def chat_genetics(
    command: AskGeneticsQuestionCommand,
    service: LLMGenerationService = Depends(get_llm_service),
    settings: Settings = Depends(get_settings),
) -> ChatAnswerOutput:
    """Answer a genetics question through the migrated interface layer."""
    if not settings.llm_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not configured: set PROXYAPI_KEY in the environment",
        )

    handler = AskGeneticsQuestionHandler(service)
    return await handler(command)


@router.get("/logs", dependencies=[Depends(require_admin_api_key)])
async def get_llm_logs(
    skip: int = 0,
    limit: int = 100,
    request_type: LLMRequestType | None = None,
    fallback_only: bool = False,
    repository: LLMLogRepositoryImpl = Depends(get_llm_log_repository),
) -> LLMLogListOutput:
    """List llm logs with simple filters for admin inspection."""
    handler = GetLLMLogsHandler(repository)
    return await handler(
        GetLLMLogsQuery(
            skip=skip,
            limit=limit,
            request_type=request_type,
            fallback_only=fallback_only,
        )
    )


@router.get("/stats", dependencies=[Depends(require_admin_api_key)])
async def get_llm_stats(
    repository: LLMLogRepositoryImpl = Depends(get_llm_log_repository),
) -> LLMStatsOutput:
    """Return aggregated llm monitoring statistics."""
    handler = GetLLMStatsHandler(repository)
    return await handler(GetLLMStatsQuery())
