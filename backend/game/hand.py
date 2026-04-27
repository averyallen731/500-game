"""
Hand analysis and kitty discard heuristics.
"""
from dataclasses import dataclass
from collections import Counter
from .cards import Card, Suit, Rank, JOKER


_PLAIN_SUITS = [Suit.SPADES, Suit.CLUBS, Suit.HEARTS, Suit.DIAMONDS]


@dataclass
class HandAnalysis:
    """Summary statistics about a hand relative to a trump suit."""
    trump: Suit
    trump_count: int                    # joker + bowers + plain trump
    suit_lengths: dict[Suit, int]       # effective lengths (left bower counts as trump)
    void_suits: list[Suit]              # non-trump suits with 0 effective cards
    has_joker: bool
    has_right_bower: bool
    has_left_bower: bool
    high_card_points: int               # A=4, K=3, Q=2, J=1 (non-bower jacks only)


def analyze_hand(hand: list[Card], trump: Suit) -> HandAnalysis:
    """Return a HandAnalysis for the given hand and trump suit."""
    counts: Counter = Counter()
    has_joker = has_right_bower = has_left_bower = False
    hcp = 0

    for card in hand:
        if card.is_joker():
            has_joker = True
            if trump != Suit.NO_TRUMP:
                counts[trump] += 1
            # In NT the joker has no suit — not counted in any suit length
        elif card.is_right_bower(trump):
            has_right_bower = True
            counts[trump] += 1
        elif card.is_left_bower(trump):
            has_left_bower = True
            counts[trump] += 1
        else:
            counts[card.suit] += 1
            if card.rank == Rank.ACE:
                hcp += 4
            elif card.rank == Rank.KING:
                hcp += 3
            elif card.rank == Rank.QUEEN:
                hcp += 2
            elif card.rank == Rank.JACK:
                hcp += 1

    suit_lengths = dict(counts)

    # Void = suit present in the deck but not in this hand (exclude trump itself)
    non_trump_suits = [s for s in _PLAIN_SUITS if s != trump]
    void_suits = [s for s in non_trump_suits if counts[s] == 0]

    return HandAnalysis(
        trump=trump,
        trump_count=counts.get(trump, 0),
        suit_lengths=suit_lengths,
        void_suits=void_suits,
        has_joker=has_joker,
        has_right_bower=has_right_bower,
        has_left_bower=has_left_bower,
        high_card_points=hcp,
    )


# ── Keep / danger scoring ─────────────────────────────────────────────────────

def _keep_score(card: Card, trump: Suit) -> int:
    """
    How valuable this card is to KEEP in a normal (trick-winning) contract.
    Higher = more important to keep. Discard the 3 lowest-scored cards.
    """
    if card.is_joker():
        return 1000
    if trump != Suit.NO_TRUMP:
        if card.is_right_bower(trump):
            return 999
        if card.is_left_bower(trump):
            return 998
        if card.suit == trump:
            return 100 + card.rank.value   # 103 (3♥/3♦) – 114 (A)
    # Non-trump: prefer high cards
    return card.rank.value  # 3–14


def _danger_score(card: Card, trump: Suit) -> int:
    """
    How likely this card is to WIN a trick.
    Used for nullo: discard the 3 highest-danger cards first.
    """
    if card.is_joker():
        return 1000   # always wins — top discard priority in nullo
    if trump != Suit.NO_TRUMP:
        if card.is_right_bower(trump):
            return 999
        if card.is_left_bower(trump):
            return 998
        if card.suit == trump:
            return 100 + card.rank.value
    return card.rank.value


# ── Public interface ──────────────────────────────────────────────────────────

def best_kitty_discard(
    hand_14: list[Card],
    trump: Suit,
    nullo: bool = False,
) -> tuple[list[Card], list[Card]]:
    """
    Choose 3 cards to discard from a 14-card hand (original 11 + 3 kitty).
    Returns (kept_11, discarded_3).

    Normal contract  → keep trump / high cards, discard low off-suit cards.
    Nullo contract   → discard highest-danger cards first (joker, trump, aces).
    """
    if len(hand_14) != 14:
        raise ValueError(f"Expected 14 cards, got {len(hand_14)}")

    if nullo:
        ordered = sorted(hand_14, key=lambda c: _danger_score(c, trump), reverse=True)
    else:
        ordered = sorted(hand_14, key=lambda c: _keep_score(c, trump))

    discarded = ordered[:3]
    kept = ordered[3:]
    return kept, discarded
