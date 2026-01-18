from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ...db.session import get_db
from ...db.models.gene import Gene
from ...schemas.gene import GeneCreate, GeneUpdate, GeneResponse

router = APIRouter()


@router.get("/", response_model=List[GeneResponse])
async def list_genes(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех генов"""
    query = select(Gene)
    
    if active_only:
        query = query.where(Gene.is_active == True)
    
    query = query.offset(skip).limit(limit).order_by(Gene.name)
    result = await db.execute(query)
    genes = result.scalars().all()
    
    return genes


@router.get("/{gene_id}", response_model=GeneResponse)
async def get_gene(gene_id: int, db: AsyncSession = Depends(get_db)):
    """Получить ген по ID"""
    gene = await db.get(Gene, gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ген не найден"
        )
    return gene


@router.post("/", response_model=GeneResponse, status_code=status.HTTP_201_CREATED)
async def create_gene(gene_data: GeneCreate, db: AsyncSession = Depends(get_db)):
    """Создать новый ген"""
    # Проверка уникальности
    query = select(Gene).where(Gene.name == gene_data.name.upper())
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ген {gene_data.name} уже существует"
        )
    
    gene = Gene(**gene_data.model_dump())
    db.add(gene)
    await db.commit()
    await db.refresh(gene)
    
    return gene


@router.put("/{gene_id}", response_model=GeneResponse)
async def update_gene(
    gene_id: int,
    gene_data: GeneUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить ген"""
    gene = await db.get(Gene, gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ген не найден"
        )
    
    for field, value in gene_data.model_dump(exclude_unset=True).items():
        setattr(gene, field, value)
    
    await db.commit()
    await db.refresh(gene)
    
    return gene


@router.delete("/{gene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gene(gene_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить ген (soft delete - деактивация)"""
    gene = await db.get(Gene, gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ген не найден"
        )
    
    gene.is_active = False
    await db.commit()
    
    return None
