"""
Тесты ORM-моделей и их свойств/методов.

Проверяем: что модели корректно сохраняются в БД,
каскадные удаления, вычисляемые свойства.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.models.game import GameAttempt, GameSession
from src.app.db.models.gene import Gene
from src.app.db.models.prize import PrizeType, UserPrize
from src.app.db.models.user import User


class TestGene:

    @pytest.mark.asyncio
    async def test_length_property(self, db, make_gene):
        gene = await make_gene(name="MTHFR")
        assert gene.length == 5

    @pytest.mark.asyncio
    async def test_length_for_longer_name(self, db, make_gene):
        gene = await make_gene(name="TCF7L2")
        assert gene.length == 6

    @pytest.mark.asyncio
    async def test_unique_name_constraint(self, db, gene):
        duplicate = Gene(
            name=gene.name,
            description="Дубликат",
            hint="hint",
            difficulty="easy",
        )
        db.add(duplicate)
        with pytest.raises(Exception):  # IntegrityError или аналог
            await db.commit()

    @pytest.mark.asyncio
    async def test_is_active_default_true(self, db):
        gene = Gene(
            name="APOE4",
            description="Тест",
            hint="hint",
            difficulty="easy",
        )
        db.add(gene)
        await db.commit()
        await db.refresh(gene)
        assert gene.is_active is True


class TestUser:

    @pytest.mark.asyncio
    async def test_unique_telegram_id(self, db, user):
        duplicate = User(
            telegram_id=user.telegram_id,
            username="other",
        )
        db.add(duplicate)
        with pytest.raises(Exception):
            await db.commit()

    @pytest.mark.asyncio
    async def test_username_nullable(self, db):
        u = User(telegram_id=42, username=None)
        db.add(u)
        await db.commit()
        await db.refresh(u)
        assert u.username is None

    @pytest.mark.asyncio
    async def test_cascade_delete_game_sessions(self, db, user, gene, make_game_session):
        """При удалении пользователя его игры тоже удаляются."""
        session = await make_game_session(user_id=user.id, gene_id=gene.id)
        session_id = session.id

        await db.delete(user)
        await db.commit()

        found = await db.get(GameSession, session_id)
        assert found is None


class TestGameSession:

    @pytest.mark.asyncio
    async def test_default_values(self, db, user, gene, make_game_session):
        session = await make_game_session(user_id=user.id, gene_id=gene.id)

        assert session.attempts == 0
        assert session.is_won is False
        assert session.is_finished is False
        assert session.hint_used is False
        assert session.points_earned == 0
        assert session.finished_at is None

    @pytest.mark.asyncio
    async def test_cascade_delete_attempts(self, db, user, gene, make_game_session):
        """При удалении сессии удаляются и попытки."""
        session = await make_game_session(user_id=user.id, gene_id=gene.id)

        attempt = GameAttempt(
            session_id=session.id,
            attempt_number=1,
            guess_word="XXXXX",
            result=[{"letter": "X", "status": "absent"}] * 5,
        )
        db.add(attempt)
        await db.commit()
        attempt_id = attempt.id

        await db.delete(session)
        await db.commit()

        found = await db.get(GameAttempt, attempt_id)
        assert found is None


class TestPrizeType:

    @pytest.mark.asyncio
    async def test_created_active_by_default(self, db, make_prize_type):
        prize = await make_prize_type()
        assert prize.is_active is True

    @pytest.mark.asyncio
    async def test_can_be_deactivated(self, db, make_prize_type):
        prize = await make_prize_type(is_active=False)
        assert prize.is_active is False

    @pytest.mark.asyncio
    async def test_toggle_active(self, db, make_prize_type):
        prize = await make_prize_type(is_active=True)
        prize.is_active = False
        await db.commit()
        await db.refresh(prize)
        assert prize.is_active is False
