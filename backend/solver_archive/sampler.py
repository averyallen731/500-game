"""
Random deal sampler.

Given the user's 11-card hand (South, seat 2), randomly distributes the
remaining 36 cards to North (partner, seat 0), East (seat 1), West (seat 3),
and the kitty (3 cards).
"""
import random
from backend.game.cards import Card
from backend.game.deck import build_deck
from backend.game.tricks import SOUTH


def sample_remaining(
    known_hand: list[Card],
    rng: random.Random = None,
) -> dict:
    """
    Given the user's hand (South, seat 2), randomly deal the remaining
    36 cards to North (partner), East, West, and kitty (3 cards).

    Returns:
        {
            'hands': list[list[Card]],   # hands[seat] for seats 0-3
            'kitty': list[Card],         # 3-card kitty
        }
    where hands[2] == known_hand (unchanged).

    The remaining 36 cards = 47 - 11 = 36.
    Split: North 11, East 11, West 11, kitty 3.
    """
    if rng is None:
        rng = random.Random()

    full_deck = build_deck()
    known_set = set(id(c) for c in known_hand)  # avoid mutable issues
    known_cards = set(known_hand)

    remaining = [c for c in full_deck if c not in known_cards]

    if len(remaining) != 36:
        raise ValueError(
            f"Expected 36 remaining cards, got {len(remaining)}. "
            f"User hand has {len(known_hand)} cards."
        )

    rng.shuffle(remaining)

    north_hand = remaining[0:11]
    east_hand = remaining[11:22]
    west_hand = remaining[22:33]
    kitty = remaining[33:36]

    hands: list[list[Card]] = [None, None, None, None]
    hands[0] = north_hand   # North
    hands[1] = east_hand    # East
    hands[2] = list(known_hand)  # South (user) — unchanged
    hands[3] = west_hand    # West

    return {'hands': hands, 'kitty': kitty}
