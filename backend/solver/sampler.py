"""
Deals the 36 remaining cards (unknown to the declarer) to three other seats + kitty.
"""
import random

from backend.game.cards import Card
from backend.game.deck import build_deck


def sample_remaining(
    known_hand: list[Card],
    declarer_seat: int,
    rng: random.Random,
) -> tuple[list[list[Card]], list[Card]]:
    """
    Given the declarer's 11-card known hand, randomly distribute the remaining
    36 cards to the other three seats (11 each) and a 3-card kitty.

    Returns (hands, kitty) where:
      hands[declarer_seat] = known_hand
      hands[other seats]   = 11 random cards each
      kitty                = 3 random cards (face-down, not dealt to anyone)
    """
    deck = build_deck()
    known_set = set(known_hand)
    remaining = [c for c in deck if c not in known_set]
    assert len(remaining) == 36, f"Expected 36 remaining cards, got {len(remaining)}"

    rng.shuffle(remaining)

    other_seats = [s for s in range(4) if s != declarer_seat]
    hands: list[list[Card]] = [[] for _ in range(4)]
    hands[declarer_seat] = list(known_hand)

    for i, seat in enumerate(other_seats):
        hands[seat] = remaining[i * 11 : (i + 1) * 11]

    kitty = remaining[33:]  # last 3 cards
    return hands, kitty
