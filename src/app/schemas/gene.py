from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class GeneBase(BaseModel):
    """Базовая схема гена"""
    name: str = Field(..., min_length=5, max_length=7, description="Название гена")
    description: str = Field(..., min_length=20, description="Описание гена")
    hint: str = Field(..., min_length=10, description="Подсказка")
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    
    @field_validator("name")
    def name_uppercase(cls, v):
        return v.upper()


class GeneCreate(GeneBase):
    """Схема создания гена"""
    is_active: bool = True


class GeneUpdate(BaseModel):
    """Схема обновления гена"""
    name: Optional[str] = Field(None, min_length=5, max_length=7)
    description: Optional[str] = Field(None, min_length=20)
    hint: Optional[str] = Field(None, min_length=10)
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    is_active: Optional[bool] = None


class GeneResponse(GeneBase):
    """Схема ответа с геном"""
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
