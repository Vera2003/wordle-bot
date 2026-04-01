"""initial

Revision ID: 0354ae9d502b
Revises:
Create Date: 2026-03-05 13:04:27.565690

"""

from alembic import op

from src.infrastructure.db.base import Base
from src.infrastructure.db.models import (  # noqa: F401
    AchievementTypeModel,
    GameAttemptModel,
    GameSessionModel,
    GeneModel,
    LLMLogModel,
    PrizeModel,
    UserAchievementModel,
    UserModel,
    UserPrizeModel,
)


# revision identifiers, used by Alembic.
revision = '0354ae9d502b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
