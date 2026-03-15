"""Unit tests for game domain layer."""

import pytest
from uuid import uuid4

from src.domain.game.entities import GameSession, GameAttempt
from src.domain.game.value_objects import Word, LetterStatus, GuessResult
from src.domain.game.errors import (
    GameAlreadyFinishedError,
    NoAttemptsLeftError,
    InvalidGuessError,
)


class TestWord:
    """Tests for Word value object."""
    
    def test_create_word(self):
        """Word can be created."""
        word = Word("python")
        assert word.value == "PYTHON"
        assert word.length() == 6
    
    def test_word_case_insensitive(self):
        """Word is always uppercase."""
        assert Word("hello").value == "HELLO"
        assert Word("HELLO").value == "HELLO"
        assert Word("HeLLo").value == "HELLO"
    
    def test_word_too_long(self):
        """Word must respect max length."""
        with pytest.raises(ValueError):
            Word("a" * 30)  # Exceeds default max of 20
    
    def test_word_empty_raises(self):
        """Empty string is not a valid word."""
        with pytest.raises(ValueError):
            Word("")
    
    def test_word_equality(self):
        """Two words with same value are equal."""
        w1 = Word("hello")
        w2 = Word("HELLO")
        assert w1 == w2
    
    def test_word_hash(self):
        """Words can be used in sets/dicts."""
        w1 = Word("hello")
        w2 = Word("hello")
        s = {w1, w2}
        assert len(s) == 1  # Duplicates removed


class TestLetterStatus:
    """Tests for LetterStatus value object."""
    
    def test_create_letter_status(self):
        """LetterStatus can be created."""
        ls = LetterStatus("A", "correct")
        assert ls.letter == "A"
        assert ls.status == "correct"
    
    def test_letter_uppercase(self):
        """Letter is always uppercase."""
        ls = LetterStatus("a", "present")
        assert ls.letter == "A"
    
    def test_invalid_status_raises(self):
        """Invalid status raises error."""
        with pytest.raises(ValueError):
            LetterStatus("A", "invalid")
    
    def test_multi_char_raises(self):
        """Only single character allowed."""
        with pytest.raises(ValueError):
            LetterStatus("AB", "correct")
    
    def test_status_checks(self):
        """Status check methods work."""
        correct = LetterStatus("A", "correct")
        assert correct.is_correct()
        assert not correct.is_present()
        assert not correct.is_absent()


class TestGuessResult:
    """Tests for GuessResult value object."""
    
    def test_exact_match(self):
        """Exact match when all letters correct."""
        letters = [
            LetterStatus("P", "correct"),
            LetterStatus("Y", "correct"),
        ]
        result = GuessResult(letters)
        assert result.is_exact_match()
    
    def test_not_exact_match(self):
        """Not exact match if some letters wrong."""
        letters = [
            LetterStatus("P", "correct"),
            LetterStatus("Y", "present"),
        ]
        result = GuessResult(letters)
        assert not result.is_exact_match()
    
    def test_count_methods(self):
        """Count methods work."""
        letters = [
            LetterStatus("P", "correct"),
            LetterStatus("Y", "present"),
            LetterStatus("T", "absent"),
        ]
        result = GuessResult(letters)
        assert result.correct_count() == 1
        assert result.present_count() == 1


class TestGameSession:
    """Tests for GameSession aggregate root."""
    
    def test_create_game(self):
        """Game can be created."""
        game = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
            max_attempts=6,
        )
        assert game.attempt_count == 0
        assert game.attempts_left == 6
        assert game.max_attempts == 6
        assert not game.is_won
        assert not game.is_finished
    
    def test_make_correct_guess(self):
        """Correct guess wins the game."""
        game = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
        )
        
        attempt = game.make_attempt(Word("python"))
        
        assert attempt.is_correct()
        assert game.is_won
        assert game.is_finished
        assert game.attempt_count == 1
        assert game.points_earned > 0
    
    def test_make_wrong_guess(self):
        """Wrong guess doesn't win."""
        game = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
        )
        
        attempt = game.make_attempt(Word("random"))
        
        assert not attempt.is_correct()
        assert not game.is_won
        assert not game.is_finished
        assert game.attempts_left == 5
    
    def test_multiple_attempts(self):
        """Can make multiple attempts."""
        game = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
            max_attempts=3,
        )
        
        game.make_attempt(Word("random"))
        assert game.attempt_count == 1
        
        game.make_attempt(Word("hello_"))
        assert game.attempt_count == 2
        
        game.make_attempt(Word("python"))
        assert game.is_won
        assert game.attempt_count == 3
    
    def test_lose_game(self):
        """Game lost when no attempts left."""
        game = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
            max_attempts=2,
        )
        
        game.make_attempt(Word("random"))
        assert not game.is_finished
        
        game.make_attempt(Word("hello_"))
        assert game.is_finished
        assert not game.is_won
        assert game.points_earned == 0
    
    def test_cannot_attempt_finished_game(self):
        """Cannot make attempt on finished game."""
        game = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
        )
        
        game.make_attempt(Word("python"))
        
        with pytest.raises(GameAlreadyFinishedError):
            game.make_attempt(Word("other_"))
    
    def test_wrong_word_length_raises(self):
        """Word must be same length as target."""
        game = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
        )
        
        with pytest.raises(InvalidGuessError):
            game.make_attempt(Word("abc"))  # Too short
    
    def test_guess_result_details(self):
        """Make attempt returns detailed result."""
        game = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
        )
        
        # Guess: "pothan" - P correct, O present, rest some correct
        attempt = game.make_attempt(Word("pothan"))
        result = attempt.result
        
        # Check result structure
        assert len(result.letters) == 6
        assert result.letters[0].letter == "P"  # Correct position


class TestGamePoints:
    """Tests for points calculation."""
    
    def test_more_points_for_fewer_attempts(self):
        """Fewer attempts = more points."""
        # Win on first attempt
        game1 = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
            max_attempts=6,
        )
        game1.make_attempt(Word("python"))
        points1 = game1.points_earned
        
        # Win on third attempt
        game2 = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
            max_attempts=6,
        )
        game2.make_attempt(Word("hello_"))
        game2.make_attempt(Word("world_"))
        game2.make_attempt(Word("python"))
        points2 = game2.points_earned
        
        # First win should have more points
        assert points1 > points2
        assert points1 > 0
        assert points2 > 0
    
    def test_no_points_for_loss(self):
        """Lost game = 0 points."""
        game = GameSession(
            id=uuid4(),
            user_id=uuid4(),
            target_word=Word("python"),
            max_attempts=1,
        )
        
        game.make_attempt(Word("random"))
        
        assert game.is_finished
        assert not game.is_won
        assert game.points_earned == 0
