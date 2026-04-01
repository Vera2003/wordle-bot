"""Gene domain services - domain logic that spans multiple entities."""

from .entities import Gene


class GeneService:
    """
    Domain Service: Business logic for genes.

    This service contains rules that don't belong to a single Gene entity.
    """

    @staticmethod
    def get_max_attempts_for_difficulty(gene: Gene) -> int:
        """
        Determine max attempts allowed for a gene based on difficulty.

        Rules:
        - easy: 10 attempts (longer, more forgiving)
        - medium: 8 attempts (balanced)
        - hard: 6 attempts (short word, challenging)
        """
        if gene.difficulty.is_easy():
            return 10
        elif gene.difficulty.is_medium():
            return 8
        else:  # hard
            return 6

    @staticmethod
    def calculate_base_points(gene: Gene, attempts_used: int) -> int:
        """
        Calculate base points earned for solving a gene.

        Rules:
        - easy: 10 points per attempt remaining
        - medium: 20 points per attempt remaining
        - hard: 50 points per attempt remaining

        Example: Solved hard gene in 3 attempts (3 left) = 50 * 3 = 150 points
        """
        max_attempts = GeneService.get_max_attempts_for_difficulty(gene)
        attempts_left = max_attempts - attempts_used

        if gene.difficulty.is_easy():
            return max(0, 10 * attempts_left)
        elif gene.difficulty.is_medium():
            return max(0, 20 * attempts_left)
        else:  # hard
            return max(0, 50 * attempts_left)
