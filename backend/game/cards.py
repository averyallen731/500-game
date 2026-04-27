from enum import Enum
from dataclasses import dataclass
from typing import Optional


class Suit(Enum):
    SPADES = "S"
    CLUBS = "C"
    HEARTS = "H"
    DIAMONDS = "D"
    NO_TRUMP = "NT"


_SAME_COLOR: dict["Suit", "Suit"] = {}  # filled after class definition


class Rank(Enum):
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


_SAME_COLOR = {
    Suit.SPADES: Suit.CLUBS,
    Suit.CLUBS: Suit.SPADES,
    Suit.HEARTS: Suit.DIAMONDS,
    Suit.DIAMONDS: Suit.HEARTS,
}


@dataclass(frozen=True)
class Card:
    suit: Optional[Suit]  # None for the Joker
    rank: Optional[Rank]  # None for the Joker

    def is_joker(self) -> bool:
        return self.suit is None

    def is_right_bower(self, trump: Suit) -> bool:
        if trump == Suit.NO_TRUMP or self.is_joker():
            return False
        return self.rank == Rank.JACK and self.suit == trump

    def is_left_bower(self, trump: Suit) -> bool:
        if trump == Suit.NO_TRUMP or self.is_joker():
            return False
        if self.rank != Rank.JACK:
            return False
        return self.suit == _SAME_COLOR.get(trump)

    def effective_suit(self, trump: Suit) -> Optional[Suit]:
        """Suit for following-suit purposes. Joker in NT has no fixed suit."""
        if self.is_joker():
            return trump if trump != Suit.NO_TRUMP else None
        if self.is_left_bower(trump):
            return trump
        return self.suit

    def __repr__(self) -> str:
        if self.is_joker():
            return "Joker"
        rank_str = {
            Rank.THREE: "3", Rank.FOUR: "4", Rank.FIVE: "5",
            Rank.SIX: "6", Rank.SEVEN: "7", Rank.EIGHT: "8",
            Rank.NINE: "9", Rank.TEN: "10", Rank.JACK: "J",
            Rank.QUEEN: "Q", Rank.KING: "K", Rank.ACE: "A",
        }[self.rank]
        return f"{rank_str}{self.suit.value}"


JOKER = Card(suit=None, rank=None)


def card_rank_in_context(card: Card, trump: Suit, led_suit: Suit) -> int:
    """
    Returns a comparison integer for trick-winning purposes. 0 = cannot win.

    Trump scale (100+): 3=103..A=114, left bower=115, right bower=116, joker=117
    Led-suit scale (1-14): rank.value
    Off-suit: 0

    The joker always returns 117 regardless of contract.
    In NT there are no bowers; the joker still wins everything.
    """
    if card.is_joker():
        return 117

    if trump != Suit.NO_TRUMP:
        if card.is_right_bower(trump):
            return 116
        if card.is_left_bower(trump):
            return 115
        if card.suit == trump:
            return 100 + card.rank.value  # 103 (3♥/3♦) – 114 (A)

    # Non-trump card (or NT contract): wins only if led suit was followed
    if card.suit == led_suit:
        return card.rank.value  # 3–14

    return 0  # off-suit, cannot win
