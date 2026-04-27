from typing import Optional
from .cards import Card, Suit, JOKER, card_rank_in_context


def get_led_suit(lead_card: Card, trump: Suit, nt_declared_suit: Optional[Suit] = None) -> Suit:
    """
    Returns the effective led suit for a trick.
    In NT when joker leads, the player must declare a suit explicitly.
    """
    if lead_card.is_joker() and trump == Suit.NO_TRUMP:
        if nt_declared_suit is None:
            raise ValueError("Must declare a suit when joker leads in NT")
        return nt_declared_suit
    eff = lead_card.effective_suit(trump)
    if eff is None:
        raise ValueError("Cannot determine led suit")
    return eff


def winning_card_index(
    trick: list[Card],
    trump: Suit,
    led_suit: Suit,
) -> int:
    """Returns the index of the winning card in the trick list."""
    ranks = [card_rank_in_context(c, trump, led_suit) for c in trick]
    return ranks.index(max(ranks))


def cards_following_suit(hand: list[Card], led_suit: Suit, trump: Suit) -> list[Card]:
    """
    Returns all cards in hand that must be played to follow the led suit.
    An empty list means the hand is void in that suit.

    Note: left bower counts as trump, not its natural suit.
    Note: joker in NT has no suit and never counts as following.
    """
    return [c for c in hand if c.effective_suit(trump) == led_suit]


def is_legal_play(
    card: Card,
    hand: list[Card],
    led_suit: Optional[Suit],
    trump: Suit,
) -> bool:
    """
    Returns True if playing card is a legal move.
    led_suit=None means this player is leading the trick (any card is legal).
    """
    if card not in hand:
        return False
    if led_suit is None:
        return True  # leading: free choice
    following = cards_following_suit(hand, led_suit, trump)
    if following:
        return card in following  # must follow suit
    return True  # void: any card is legal


def legal_plays(hand: list[Card], led_suit: Optional[Suit], trump: Suit) -> list[Card]:
    """Returns all legal cards the current player may play."""
    if led_suit is None:
        return list(hand)
    following = cards_following_suit(hand, led_suit, trump)
    return following if following else list(hand)


def play_order(leader_seat: int, active_seats: tuple[int, ...] = (0, 1, 2, 3)) -> list[int]:
    """
    Returns the ordered list of seats for one trick, starting from the leader
    and going clockwise, skipping any seats not in active_seats.

    Examples:
      play_order(2)              → [2, 3, 0, 1]  (standard 4-player, South leads)
      play_order(2, (1, 2, 3))  → [2, 3, 1]     (Nullo: North sits out, South leads)
      play_order(3, (1, 2, 3))  → [3, 1, 2]     (Nullo: North sits out, West leads)
    """
    seats = list(active_seats)
    n = len(seats)
    start = seats.index(leader_seat)
    return [seats[(start + i) % n] for i in range(n)]


def winning_seat(
    trick_cards: list[Card],
    trump: Suit,
    led_suit: Suit,
    playing_seats: list[int] | int,
) -> int:
    """
    Returns the seat number (0–3) of the trick winner.

    playing_seats: ordered list of seats that played each card
                   (playing_seats[0] is the leader).
                   Pass a plain int as a shortcut for standard 4-player games
                   — it is treated as the leader seat and expands to
                   [(leader+i)%4 for i in range(4)].

    Use play_order() to build the list for Nullo (3-player) games.
    """
    if isinstance(playing_seats, int):
        leader = playing_seats
        playing_seats = [(leader + i) % 4 for i in range(4)]
    winner_idx = winning_card_index(trick_cards, trump, led_suit)
    return playing_seats[winner_idx]


# Seat constants (used throughout the codebase)
NORTH = 0
EAST  = 1
SOUTH = 2   # human / declarer
WEST  = 3

DECLARER_SEAT = SOUTH
PARTNER_SEAT  = NORTH
OPPONENTS     = (EAST, WEST)


def is_declarer_team(seat: int) -> bool:
    """
    True if seat is on the declaring team in a normal contract (South + North).
    For Nullo/Double Nullo, use Contract.is_declarer_side() instead.
    """
    return seat in (DECLARER_SEAT, PARTNER_SEAT)
