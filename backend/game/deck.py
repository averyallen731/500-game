import random
from .cards import Card, Suit, Rank, JOKER


# Red suits include rank 3; black suits start at 4
_RED_SUITS = (Suit.HEARTS, Suit.DIAMONDS)
_BLACK_SUITS = (Suit.SPADES, Suit.CLUBS)


def build_deck() -> list[Card]:
    """Returns the 47-card 500 deck: 3-A red, 4-A black, one joker."""
    deck: list[Card] = []
    for suit in _RED_SUITS:
        for rank in Rank:  # THREE through ACE (all 12)
            deck.append(Card(suit=suit, rank=rank))
    for suit in _BLACK_SUITS:
        for rank in Rank:
            if rank == Rank.THREE:
                continue  # black suits start at 4
            deck.append(Card(suit=suit, rank=rank))
    deck.append(JOKER)
    return deck


def deal(rng: random.Random | None = None) -> tuple[list[list[Card]], list[Card]]:
    """
    Shuffles and deals 4 hands of 11 cards + 3-card kitty.
    Returns (hands, kitty) where hands[0]=North, [1]=East, [2]=South, [3]=West.
    Seat 2 (South) is always the human player.
    """
    if rng is None:
        rng = random.Random()
    deck = build_deck()
    rng.shuffle(deck)
    hands = [deck[i * 11:(i + 1) * 11] for i in range(4)]
    kitty = deck[44:]
    return hands, kitty
