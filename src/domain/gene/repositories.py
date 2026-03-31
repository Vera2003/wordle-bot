"""Gene repository abstractions (ports)."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .entities import Gene


class GeneRepository(ABC):
    """
    Port: repository for Gene persistence.
    
    This interface defines how Gene can be saved, loaded, and queried.
    Implementation is in infrastructure layer (SQLAlchemy).
    """
    
    @abstractmethod
    async def save(self, gene: Gene) -> None:
        """Save a gene (create or update)."""
        pass
    
    @abstractmethod
    async def get_by_id(self, gene_id: UUID) -> Optional[Gene]:
        """Get gene by ID."""
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Gene]:
        """Get gene by name (unique lookup)."""
        pass
    
    @abstractmethod
    async def get_active_genes(self) -> list[Gene]:
        """Get all active genes (can be used in games)."""
        pass
    
    @abstractmethod
    async def get_random_active(self) -> Optional[Gene]:
        """Get a random active gene."""
        pass
    
    @abstractmethod
    async def delete(self, gene_id: UUID) -> None:
        """Delete a gene."""
        pass
