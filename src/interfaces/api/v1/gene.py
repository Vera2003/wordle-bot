"""Gene API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.gene import (
    ActivateGeneCommand,
    ActivateGeneHandler,
    CreateGeneCommand,
    CreateGeneHandler,
    DeactivateGeneCommand,
    DeactivateGeneHandler,
    GeneOutput,
    GeneSummaryOutput,
    GetActiveGenesHandler,
    GetActiveGenesQuery,
    GetGeneByIdHandler,
    GetGeneByIdQuery,
    GetRandomActiveGeneHandler,
    GetRandomActiveGeneQuery,
)
from src.domain.gene import GeneNotFoundError
from src.infrastructure.db.repositories.gene import GeneRepositoryImpl
from src.infrastructure.db.session import get_db_session
from src.interfaces.api.security import require_admin_api_key

router = APIRouter(prefix="/genes", tags=["genes"])


async def get_gene_repository(
    db: AsyncSession = Depends(get_db_session),
) -> GeneRepositoryImpl:
    """Dependency: get gene repository."""
    return GeneRepositoryImpl(db)


@router.get("/")
async def list_active_genes(
    repository: GeneRepositoryImpl = Depends(get_gene_repository),
) -> list[GeneSummaryOutput]:
    """List active genes available for play."""
    handler = GetActiveGenesHandler(repository)
    return await handler(GetActiveGenesQuery())


@router.get("/random")
async def get_random_gene(
    repository: GeneRepositoryImpl = Depends(get_gene_repository),
) -> GeneOutput:
    """Get one random active gene."""
    try:
        handler = GetRandomActiveGeneHandler(repository)
        return await handler(GetRandomActiveGeneQuery())
    except GeneNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error


@router.get("/{gene_id}")
async def get_gene(
    gene_id: UUID,
    repository: GeneRepositoryImpl = Depends(get_gene_repository),
) -> GeneOutput:
    """Get gene details by ID."""
    try:
        handler = GetGeneByIdHandler(repository)
        return await handler(GetGeneByIdQuery(gene_id=gene_id))
    except GeneNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_api_key)],
)
async def create_gene(
    command: CreateGeneCommand,
    repository: GeneRepositoryImpl = Depends(get_gene_repository),
) -> GeneOutput:
    """Create a new gene definition."""
    try:
        handler = CreateGeneHandler(repository)
        return await handler(command)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error


@router.post("/{gene_id}/activate", dependencies=[Depends(require_admin_api_key)])
async def activate_gene(
    gene_id: UUID,
    repository: GeneRepositoryImpl = Depends(get_gene_repository),
) -> GeneOutput:
    """Activate an existing gene."""
    try:
        handler = ActivateGeneHandler(repository)
        return await handler(ActivateGeneCommand(gene_id=gene_id))
    except GeneNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error


@router.delete(
    "/{gene_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_api_key)],
)
async def deactivate_gene(
    gene_id: UUID,
    repository: GeneRepositoryImpl = Depends(get_gene_repository),
) -> Response:
    """Soft delete a gene by deactivating it."""
    try:
        handler = DeactivateGeneHandler(repository)
        await handler(DeactivateGeneCommand(gene_id=gene_id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except GeneNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error
