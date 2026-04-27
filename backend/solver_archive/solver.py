"""
Public API for the double-dummy solver.

solve()         - solve a full deal, returns declaring-side trick count
best_discard()  - pick the best 3 cards to discard from a 14-card hand
"""
from itertools import combinations
from typing import Optional

from backend.game.cards import Card, Suit
from backend.game.bidding import Contract
from backend.game.hand import _keep_score, _danger_score
from backend.solver.minimax import solve as _minimax_solve


def solve(
    hands: list[list[Card]],
    contract: Contract,
    leader: int = None,
) -> int:
    """
    Returns the number of tricks the declaring side wins with perfect play.

    hands[seat] is the list of Cards for that seat (seats 0-3).
    leader defaults to contract.declarer (leads the first trick).
    """
    return _minimax_solve(hands, contract, leader)


def best_discard(
    hand_14: list[Card],
    contract: Contract,
    other_hands: Optional[list[Optional[list[Card]]]] = None,
) -> tuple[list[Card], list[Card]]:
    """
    Declarer has 14 cards (11-card hand + 3 kitty).
    Returns (best_11_card_hand, discarded_3).

    Uses a greedy scoring approach rather than exhaustive search (364 solves
    per call would be too slow during sampling).  For nullo contracts the
    highest-danger cards are discarded first; for normal contracts the lowest
    keep-score cards are discarded.

    If other_hands is provided (list of 4 entries, None for unknown / the
    declarer seat), an exhaustive search is done instead (useful for tests).
    """
    if len(hand_14) != 14:
        raise ValueError(f"Expected 14 cards, got {len(hand_14)}")

    trump = contract.trump if contract.trump is not None else Suit.NO_TRUMP
    is_nullo = contract.bid.is_nullo or contract.bid.is_double_nullo

    if other_hands is not None:
        # Exhaustive: try all C(14,3) = 364 combos, pick best
        best_tricks = -1 if not is_nullo else 12
        best_kept: list[Card] = []
        best_discarded: list[Card] = []

        for discarded in combinations(hand_14, 3):
            kept = [c for c in hand_14 if c not in discarded]
            # Build full hands
            full_hands = list(other_hands)
            full_hands[contract.declarer] = kept
            try:
                tricks = _minimax_solve(full_hands, contract)
            except Exception:
                continue
            if is_nullo:
                if tricks < best_tricks:
                    best_tricks = tricks
                    best_kept = kept
                    best_discarded = list(discarded)
            else:
                if tricks > best_tricks:
                    best_tricks = tricks
                    best_kept = kept
                    best_discarded = list(discarded)

        if best_kept:
            return best_kept, best_discarded
        # Fallback to greedy if exhaustive fails
        is_nullo_flag = is_nullo

    else:
        is_nullo_flag = is_nullo

    # Greedy: score each card and keep the best 11
    if is_nullo_flag:
        ordered = sorted(hand_14, key=lambda c: _danger_score(c, trump), reverse=True)
    else:
        ordered = sorted(hand_14, key=lambda c: _keep_score(c, trump))

    discarded = ordered[:3]
    kept = ordered[3:]
    return kept, discarded
