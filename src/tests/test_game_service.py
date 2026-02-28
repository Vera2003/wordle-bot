"""
Тесты GameService.

check_guess — чистая функция, тестируется без БД.
start_game / make_attempt / get_user_stats — требуют БД.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.game_service import GameService


# ---------------------------------------------------------------------------
# check_guess — чистая функция
# ---------------------------------------------------------------------------

class TestCheckGuess:
    """Юнит-тесты алгоритма проверки слова Wordle."""

    def setup_method(self):
        self.svc = GameService(db=None)  # type: ignore[arg-type]

    def test_all_correct(self):
        result = self.svc.check_guess("MTHFR", "MTHFR")
        assert all(r["status"] == "correct" for r in result)

    def test_all_absent(self):
        # LLLLL не пересекается с MTHFR
        result = self.svc.check_guess("MTHFR", "LLLLL")
        assert all(r["status"] == "absent" for r in result)

    def test_all_present(self):
        # ABCDE vs BCDEA — все буквы есть, но на неверных позициях
        result = self.svc.check_guess("ABCDE", "BCDEA")
        assert all(r["status"] == "present" for r in result)

    def test_mixed(self):
        # target MTHFR, guess MTTFR
        # M=correct, T=correct, T=absent (в target только один T), F=correct, R=correct
        result = self.svc.check_guess("MTHFR", "MTTFR")
        statuses = [r["status"] for r in result]
        assert statuses[0] == "correct"   # M
        assert statuses[1] == "correct"   # T (позиция 1)
        assert statuses[2] == "absent"    # T (второй T лишний)
        assert statuses[3] == "correct"   # F
        assert statuses[4] == "correct"   # R

    def test_duplicate_letter_not_double_counted(self):
        # target AABBB, guess AAAAA — только 2 A в target
        result = self.svc.check_guess("AABBB", "AAAAA")
        statuses = [r["status"] for r in result]
        assert statuses[0] == "correct"
        assert statuses[1] == "correct"
        assert statuses[2] == "absent"
        assert statuses[3] == "absent"
        assert statuses[4] == "absent"

    def test_returns_uppercased_letters(self):
        result = self.svc.check_guess("MTHFR", "mthfr")
        assert all(r["letter"] == r["letter"].upper() for r in result)

    def test_result_length_equals_word_length(self):
        result = self.svc.check_guess("TCF7L2", "AAAAAA")
        assert len(result) == 6

    def test_status_values_are_valid(self):
        result = self.svc.check_guess("MTHFR", "XXXXX")
        valid = {"correct", "present", "absent"}
        assert all(r["status"] in valid for r in result)


# ---------------------------------------------------------------------------
# start_game
# ---------------------------------------------------------------------------

class TestStartGame:

    @pytest.mark.asyncio
    async def test_creates_session(self, db: AsyncSession, user, gene):
        svc = GameService(db)
        session = await svc.start_game(user.id, gene.id)

        assert session.id is not None
        assert session.user_id == user.id
        assert session.gene_id == gene.id
        assert session.attempts == 0
        assert session.is_finished is False
        assert session.is_won is False

    @pytest.mark.asyncio
    async def test_default_max_attempts(self, db: AsyncSession, user, gene):
        svc = GameService(db)
        session = await svc.start_game(user.id, gene.id)
        assert session.max_attempts == 6

    @pytest.mark.asyncio
    async def test_returns_existing_active_session(self, db: AsyncSession, user, gene):
        """Повторный вызов возвращает ту же сессию, не создаёт новую."""
        svc = GameService(db)
        session1 = await svc.start_game(user.id, gene.id)
        session2 = await svc.start_game(user.id, gene.id)
        assert session1.id == session2.id

    @pytest.mark.asyncio
    async def test_no_genes_raises(self, db: AsyncSession, user):
        """Если генов нет — ValueError."""
        svc = GameService(db)
        with pytest.raises(ValueError, match="Нет доступных генов"):
            await svc.start_game(user.id, gene_id=None)

    @pytest.mark.asyncio
    async def test_picks_random_gene_when_id_not_given(self, db: AsyncSession, user, make_gene):
        await make_gene(name="GENE1")
        await make_gene(name="GENE2")
        svc = GameService(db)
        session = await svc.start_game(user.id, gene_id=None)
        assert session.gene_id is not None


# ---------------------------------------------------------------------------
# make_attempt
# ---------------------------------------------------------------------------

class TestMakeAttempt:

    @pytest.mark.asyncio
    async def test_wrong_length_raises(self, db, user, gene, make_game_session):
        session = await make_game_session(user_id=user.id, gene_id=gene.id)
        svc = GameService(db)
        with pytest.raises(ValueError, match="букв"):
            await svc.make_attempt(session.id, "A")

    @pytest.mark.asyncio
    async def test_finished_game_raises(self, db, user, gene, make_game_session):
        session = await make_game_session(user_id=user.id, gene_id=gene.id, is_finished=True)
        svc = GameService(db)
        with pytest.raises(ValueError, match="завершена"):
            await svc.make_attempt(session.id, gene.name)

    @pytest.mark.asyncio
    async def test_nonexistent_session_raises(self, db):
        svc = GameService(db)
        with pytest.raises(ValueError, match="не найдена"):
            await svc.make_attempt(session_id=999_999, guess="MTHFR")

    @pytest.mark.asyncio
    async def test_correct_guess_wins(self, db, user, gene, make_game_session):
        session = await make_game_session(user_id=user.id, gene_id=gene.id)
        svc = GameService(db)

        result = await svc.make_attempt(session.id, gene.name)

        assert result.is_correct is True
        assert result.is_game_over is True
        assert result.is_won is True

    @pytest.mark.asyncio
    async def test_win_awards_points(self, db, user, gene, make_game_session):
        session = await make_game_session(user_id=user.id, gene_id=gene.id)
        svc = GameService(db)

        result = await svc.make_attempt(session.id, gene.name)

        assert result.points_earned > 0
        await db.refresh(user)
        assert user.total_points == result.points_earned

    @pytest.mark.asyncio
    async def test_fewer_attempts_gives_more_points(self, db, make_user, make_gene, make_game_session):
        """Победа на 1-й попытке даёт больше очков, чем на 5-й."""
        user_a = await make_user(telegram_id=1)
        user_b = await make_user(telegram_id=2)
        gene_a = await make_gene(name="APOE4")
        gene_b = await make_gene(name="APOE5")

        session_early = await make_game_session(user_id=user_a.id, gene_id=gene_a.id, attempts=0)
        session_late  = await make_game_session(user_id=user_b.id, gene_id=gene_b.id, attempts=4)

        svc = GameService(db)
        r_early = await svc.make_attempt(session_early.id, "APOE4")
        r_late  = await svc.make_attempt(session_late.id,  "APOE5")

        assert r_early.points_earned > r_late.points_earned

    @pytest.mark.asyncio
    async def test_wrong_guess_increments_attempts(self, db, user, gene_5, make_game_session):
        session = await make_game_session(user_id=user.id, gene_id=gene_5.id)
        svc = GameService(db)

        result = await svc.make_attempt(session.id, "AAAAA")

        assert result.is_correct is False
        assert result.attempt_number == 1
        assert result.attempts_left == 5

    @pytest.mark.asyncio
    async def test_last_wrong_attempt_loses(self, db, user, gene_5, make_game_session):
        """На 6-й неверной попытке игра завершается поражением."""
        session = await make_game_session(
            user_id=user.id, gene_id=gene_5.id, attempts=5, max_attempts=6
        )
        svc = GameService(db)

        result = await svc.make_attempt(session.id, "AAAAA")

        assert result.is_game_over is True
        assert result.is_won is False
        assert result.points_earned == 0

    @pytest.mark.asyncio
    async def test_result_contains_letter_statuses(self, db, user, gene, make_game_session):
        """make_attempt возвращает статусы для каждой буквы."""
        session = await make_game_session(user_id=user.id, gene_id=gene.id)
        svc = GameService(db)

        wrong_guess = "A" * len(gene.name)
        result = await svc.make_attempt(session.id, wrong_guess)

        assert len(result.result) == len(gene.name)
        valid_statuses = {"correct", "present", "absent"}
        assert all(r.status in valid_statuses for r in result.result)


# ---------------------------------------------------------------------------
# get_user_stats
# ---------------------------------------------------------------------------

class TestGetUserStats:

    @pytest.mark.asyncio
    async def test_empty_stats(self, db, user):
        svc = GameService(db)
        stats = await svc.get_user_stats(user.id)

        assert stats["total_games"] == 0
        assert stats["won_games"] == 0
        assert stats["lost_games"] == 0
        assert stats["win_rate"] == 0
        assert stats["total_points"] == 0

    @pytest.mark.asyncio
    async def test_counts_finished_games(self, db, user, gene, make_game_session):
        await make_game_session(user_id=user.id, gene_id=gene.id, is_finished=True, is_won=True)
        await make_game_session(user_id=user.id, gene_id=gene.id, is_finished=True, is_won=False)
        # Незавершённая — не считается
        await make_game_session(user_id=user.id, gene_id=gene.id, is_finished=False)

        svc = GameService(db)
        stats = await svc.get_user_stats(user.id)

        assert stats["total_games"] == 2
        assert stats["won_games"] == 1
        assert stats["lost_games"] == 1

    @pytest.mark.asyncio
    async def test_win_rate_calculation(self, db, user, make_gene, make_game_session):
        g1 = await make_gene(name="GENE1")
        g2 = await make_gene(name="GENE2")
        g3 = await make_gene(name="GENE3")
        g4 = await make_gene(name="GENE4")

        await make_game_session(user_id=user.id, gene_id=g1.id, is_finished=True, is_won=True)
        await make_game_session(user_id=user.id, gene_id=g2.id, is_finished=True, is_won=True)
        await make_game_session(user_id=user.id, gene_id=g3.id, is_finished=True, is_won=False)
        await make_game_session(user_id=user.id, gene_id=g4.id, is_finished=True, is_won=False)

        svc = GameService(db)
        stats = await svc.get_user_stats(user.id)

        assert stats["win_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_reflects_user_total_points(self, db, make_user, gene, make_game_session):
        user = await make_user(total_points=250)
        svc = GameService(db)
        stats = await svc.get_user_stats(user.id)
        assert stats["total_points"] == 250
