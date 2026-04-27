from dataclasses import dataclass
from enum import Enum
from .cards import Suit


class BidSuit(Enum):
    SPADES = "S"
    CLUBS = "C"
    HEARTS = "H"
    DIAMONDS = "D"
    NO_TRUMP = "NT"
    NULLO = "NULLO"
    DOUBLE_NULLO = "DOUBLE_NULLO"


# Point values for each bid (standard 500 scoring)
_SUIT_ORDER = [BidSuit.SPADES, BidSuit.CLUBS, BidSuit.DIAMONDS, BidSuit.HEARTS, BidSuit.NO_TRUMP]
_BASE_POINTS = {
    6: {BidSuit.SPADES: 40, BidSuit.CLUBS: 60, BidSuit.DIAMONDS: 80, BidSuit.HEARTS: 100, BidSuit.NO_TRUMP: 120},
    7: {BidSuit.SPADES: 140, BidSuit.CLUBS: 160, BidSuit.DIAMONDS: 180, BidSuit.HEARTS: 200, BidSuit.NO_TRUMP: 220},
    8: {BidSuit.SPADES: 240, BidSuit.CLUBS: 260, BidSuit.DIAMONDS: 280, BidSuit.HEARTS: 300, BidSuit.NO_TRUMP: 320},
    9: {BidSuit.SPADES: 340, BidSuit.CLUBS: 360, BidSuit.DIAMONDS: 380, BidSuit.HEARTS: 400, BidSuit.NO_TRUMP: 420},
    10: {BidSuit.SPADES: 440, BidSuit.CLUBS: 460, BidSuit.DIAMONDS: 480, BidSuit.HEARTS: 500, BidSuit.NO_TRUMP: 520},
    11: {BidSuit.SPADES: 540, BidSuit.CLUBS: 560, BidSuit.DIAMONDS: 580, BidSuit.HEARTS: 600, BidSuit.NO_TRUMP: 620},
}


@dataclass(frozen=True)
class Bid:
    tricks: int        # 6–11 for suit/NT bids; 0 for nullo/double nullo
    suit: BidSuit

    @property
    def is_nullo(self) -> bool:
        return self.suit in (BidSuit.NULLO, BidSuit.DOUBLE_NULLO)

    @property
    def is_double_nullo(self) -> bool:
        return self.suit == BidSuit.DOUBLE_NULLO

    @property
    def point_value(self) -> int:
        if self.suit == BidSuit.NULLO:
            return 250
        if self.suit == BidSuit.DOUBLE_NULLO:
            return 500
        return _BASE_POINTS[self.tricks][self.suit]

    @property
    def trump_suit(self) -> Suit | None:
        """Maps BidSuit to game Suit. Returns None for nullo."""
        mapping = {
            BidSuit.SPADES: Suit.SPADES,
            BidSuit.CLUBS: Suit.CLUBS,
            BidSuit.HEARTS: Suit.HEARTS,
            BidSuit.DIAMONDS: Suit.DIAMONDS,
            BidSuit.NO_TRUMP: Suit.NO_TRUMP,
        }
        return mapping.get(self.suit)

    def __repr__(self) -> str:
        if self.is_nullo:
            return self.suit.value.replace("_", " ").title()
        return f"{self.tricks}{self.suit.value}"


NULLO = Bid(tricks=0, suit=BidSuit.NULLO)
DOUBLE_NULLO = Bid(tricks=0, suit=BidSuit.DOUBLE_NULLO)


@dataclass(frozen=True)
class Contract:
    """
    A won bid ready to be played out.

    Encapsulates who plays, what trump is, and what 'making it' means.

    Seat layout: 0=North, 1=East, 2=South (declarer/user), 3=West.
    Partner is always the seat directly opposite: (declarer + 2) % 4.

    Nullo rules:
      - Regular Nullo  : only the declarer plays; partner sits out (3-card tricks).
      - Double Nullo   : both partners play and both try to take zero tricks.
      - Normal contract: all four seats play.
    """
    bid: Bid
    declarer: int  # seat number of the player who won the bid

    @property
    def partner(self) -> int:
        """Seat directly opposite the declarer."""
        return (self.declarer + 2) % 4

    @property
    def trump(self):
        """Game Suit for this contract (None for nullo)."""
        return self.bid.trump_suit

    @property
    def active_seats(self) -> tuple[int, ...]:
        """
        Seats that actually play cards, in ascending order.
        Regular Nullo: partner sits out → 3 active seats.
        Everything else: all 4 seats.
        """
        all_seats = (0, 1, 2, 3)
        if self.bid.is_nullo and not self.bid.is_double_nullo:
            return tuple(s for s in all_seats if s != self.partner)
        return all_seats

    def is_declarer_side(self, seat: int) -> bool:
        """
        True if this seat is on the declaring side.
        Regular Nullo: only the declarer counts (partner is inactive).
        All other contracts: declarer + partner.
        """
        if self.bid.is_nullo and not self.bid.is_double_nullo:
            return seat == self.declarer
        return seat in (self.declarer, self.partner)

    def made_contract(self, declarer_side_tricks: int) -> bool:
        """Did the declaring side make their contract?"""
        if self.bid.is_nullo or self.bid.is_double_nullo:
            return declarer_side_tricks == 0
        return declarer_side_tricks >= self.bid.tricks

    def tricks_needed(self) -> int:
        """Tricks the declaring side must win (0 for nullo)."""
        if self.bid.is_nullo or self.bid.is_double_nullo:
            return 0
        return self.bid.tricks


def all_bids() -> list[Bid]:
    """
    Returns all valid 500 bids in ascending order of value.

    Nullo (250 pts) slots between 8S (240) and 8C (260).
    Double Nullo ties 10H at 500 pts; tiebreaker puts Double Nullo after 10H
    (in competitive bidding, Double Nullo outranks 10H when equal).
    11NT (620 pts) is the highest regular bid.
    """
    bids: list[Bid] = []
    for tricks in range(6, 12):
        for suit in _SUIT_ORDER:
            bids.append(Bid(tricks=tricks, suit=suit))
    bids.append(NULLO)
    bids.append(DOUBLE_NULLO)
    # Primary: point value. Secondary: double nullo beats regular bids at same value.
    return sorted(bids, key=lambda b: (b.point_value, 1 if b.is_double_nullo else 0))
