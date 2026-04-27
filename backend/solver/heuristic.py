"""
Rule-based card-play heuristic for 500.

play_card() returns the card the bot plays for a given seat.

Make-tricks policy (normal contracts — all four seats):
  Leading : pull trump if outstanding; cash known winners; lead top of longest suit.
  Following: third-hand-high; cover an honour; let partner win cheaply;
             ruff in when void and opponent is winning.

Nullo policy (declarer side — trying to WIN ZERO TRICKS):
  Leading : lead lowest card (least likely to win).
  Following: play highest card that stays below the current winner;
             if forced to win, play lowest; discard highest dangerous card when void.

Nullo-defence policy (opponents against nullo — trying to FORCE declarer to win):
  Leading : lead lowest non-joker (minimises declarer's room to duck under the lead).
  Following, declarer winning: play below declarer so they keep winning.
  Following, partner winning : dump highest non-beating card (clear dangerous cards safely);
                               if all cards beat partner, play lowest to avoid stealing.
  Void                       : discard highest non-joker (clear dangerous cards).
"""

import random
from backend.game.cards import Card, Suit, JOKER, card_rank_in_context
from backend.game.deck import build_deck
from backend.game.tricks import legal_plays, play_order, winning_card_index
from backend.game.bidding import Contract

# Full 47-card reference deck — used for card-counting in the heuristic
_ALL_CARDS: list[Card] = build_deck()
_PLAIN_SUITS = [Suit.SPADES, Suit.CLUBS, Suit.HEARTS, Suit.DIAMONDS]


# ── Public entry point ────────────────────────────────────────────────────────

def play_card(
    seat: int,
    hand: list[Card],
    trick_so_far: list[Card],   # cards played in this trick so far, in seat order
    leader_seat: int,           # seat that led this trick
    led_suit: Suit | None,      # effective led suit; None means this player is leading
    trump: Suit,                # Suit.NO_TRUMP for nullo and NT contracts
    contract: Contract,
    played_cards: set[Card],    # all cards played in previous completed tricks
    rng: random.Random,
) -> Card:
    """Return the card this seat should play."""
    legal = legal_plays(hand, led_suit, trump)
    if len(legal) == 1:
        return legal[0]

    is_nullo = contract.bid.is_nullo or contract.bid.is_double_nullo
    am_declarer_side = contract.is_declarer_side(seat)

    # Declarer side plays nullo (try to lose); opponents try to force them to win
    if is_nullo and am_declarer_side:
        return _play_nullo(
            seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, rng
        )
    if is_nullo and not am_declarer_side:
        return _play_nullo_defense(
            seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, rng
        )
    return _play_make_tricks(
        seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, played_cards, rng
    )


# ── Make-tricks policy ────────────────────────────────────────────────────────

def _play_make_tricks(
    seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, played_cards, rng
):
    if led_suit is None:
        return _lead_make_tricks(seat, hand, legal, trump, contract, played_cards, rng)
    return _follow_make_tricks(
        seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, rng
    )


def _lead_make_tricks(seat, hand, legal, trump, contract, played_cards, rng):
    """Choose a card to lead in a make-tricks contract."""
    trump_in_hand = [c for c in legal if c.effective_suit(trump) == trump]
    non_trump = [c for c in legal if c.effective_suit(trump) != trump]

    # Pull trump: lead highest trump if opponents may still have trump
    if trump != Suit.NO_TRUMP and trump_in_hand:
        outstanding = _outstanding_trump(trump, trump_in_hand, played_cards)
        if outstanding:
            return _highest_in_context(trump_in_hand, trump, trump)

    # Cash known winners before they get ruffed
    winners = [c for c in legal if _is_definite_winner(c, trump, hand, played_cards)]
    if winners:
        # Cash the winner in the longest suit first (establish the suit)
        return max(winners, key=lambda c: (
            len([x for x in hand if x.effective_suit(trump) == c.effective_suit(trump)]),
            card_rank_in_context(c, trump, c.effective_suit(trump) or trump),
        ))

    # Lead top of longest side suit to establish length tricks
    if non_trump:
        groups = _group_by_effective_suit(non_trump, trump)
        if groups:
            longest_suit = max(groups, key=lambda s: len(groups[s]))
            return _highest_in_context(groups[longest_suit], trump, longest_suit)

    # Only trump left; lead lowest to preserve trump control
    if trump_in_hand:
        return _lowest_in_context(trump_in_hand, trump, trump)

    return rng.choice(legal)


def _follow_make_tricks(
    seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, rng
):
    """Choose a card to follow with in a make-tricks contract."""
    play_seats = play_order(leader_seat, contract.active_seats)
    played_seats = play_seats[: len(trick_so_far)]

    win_idx = winning_card_index(trick_so_far, trump, led_suit)
    current_winner_seat = played_seats[win_idx]
    current_win_rank = card_rank_in_context(trick_so_far[win_idx], trump, led_suit)

    partner_seat = (seat + 2) % 4
    partner_winning = current_winner_seat == partner_seat

    # Cards in the led suit
    suit_cards = [c for c in legal if c.effective_suit(trump) == led_suit]
    can_follow = bool(suit_cards)

    if can_follow:
        beaters = [
            c for c in suit_cards
            if card_rank_in_context(c, trump, led_suit) > current_win_rank
        ]

        if partner_winning:
            # Partner is already winning — play low and save high cards
            return _lowest_in_context(suit_cards, trump, led_suit)

        if beaters:
            # Beat the opponent with our cheapest winning card
            return _lowest_in_context(beaters, trump, led_suit)

        # Can't beat the winner — dump our cheapest card in suit
        return _lowest_in_context(suit_cards, trump, led_suit)

    # ── Void in led suit ──────────────────────────────────────────────────────
    trump_in_hand = [c for c in legal if c.effective_suit(trump) == trump]

    if trump != Suit.NO_TRUMP and trump_in_hand and not partner_winning:
        # Ruff in: use lowest trump that beats the current winner
        winning_ruffs = [
            c for c in trump_in_hand
            if card_rank_in_context(c, trump, trump) > current_win_rank
        ]
        if winning_ruffs:
            return _lowest_in_context(winning_ruffs, trump, trump)

    # Discard: dump our cheapest card (prefer to shed from shortest suit)
    return _cheapest_discard(legal, trump)


# ── Nullo policy ──────────────────────────────────────────────────────────────

def _play_nullo(
    seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, rng
):
    """Choose a card in nullo (trying to lose all tricks)."""
    if led_suit is None:
        return _lead_nullo(legal, rng)
    return _follow_nullo(legal, trick_so_far, led_suit, trump)


def _lead_nullo(legal, rng):
    """
    Lead the card least likely to win a trick.
    Avoid leading aces; never lead the joker if possible (it always wins).
    """
    non_joker = [c for c in legal if not c.is_joker()]
    if not non_joker:
        return JOKER  # stuck

    # Lead our lowest-ranked card — least likely to win
    return min(non_joker, key=lambda c: c.rank.value)


def _follow_nullo(legal, trick_so_far, led_suit, trump):
    """
    Follow in nullo: stay below the current winner if possible.
    When void, discard our most dangerous card (highest rank, never the joker).
    """
    win_idx = winning_card_index(trick_so_far, trump, led_suit)
    current_win_rank = card_rank_in_context(trick_so_far[win_idx], trump, led_suit)

    suit_cards = [c for c in legal if c.effective_suit(trump) == led_suit]
    can_follow = bool(suit_cards)

    if can_follow:
        # Cards that stay below the current winner (safe plays)
        safe = [
            c for c in suit_cards
            if card_rank_in_context(c, trump, led_suit) < current_win_rank
        ]
        if safe:
            # Play highest safe card — dump the most dangerous safe card
            return _highest_in_context(safe, trump, led_suit)

        # All our cards win — play lowest to minimise the "wasted win"
        return _lowest_in_context(suit_cards, trump, led_suit)

    # ── Void in led suit: discard a dangerous card ────────────────────────────
    # The joker always wins, so never play it as a discard unless it's the only card
    non_joker = [c for c in legal if not c.is_joker()]
    if non_joker:
        # Discard highest non-joker card (unload aces / kings)
        return max(non_joker, key=lambda c: c.rank.value)
    return JOKER  # stuck with joker


# ── Nullo-defence policy ──────────────────────────────────────────────────────

def _play_nullo_defense(
    seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, rng
):
    """
    Opponent strategy when declarer side is playing nullo.
    Goal: force the declarer to win at least one trick.
    """
    if led_suit is None:
        # Lead LOWEST non-joker — minimises the declarer's room to duck under the lead.
        # A high lead just gives the declarer a free "play below" card.
        return _lead_nullo(legal, rng)

    # Determine who is currently winning
    play_seats = play_order(leader_seat, contract.active_seats)
    played_seats = play_seats[: len(trick_so_far)]
    win_idx = winning_card_index(trick_so_far, trump, led_suit)
    current_winner_seat = played_seats[win_idx]
    current_win_rank = card_rank_in_context(trick_so_far[win_idx], trump, led_suit)

    declarer_winning = contract.is_declarer_side(current_winner_seat)

    suit_cards = [c for c in legal if c.effective_suit(trump) == led_suit]
    can_follow = bool(suit_cards)

    if can_follow:
        if declarer_winning:
            # Declarer is winning — play below them so they keep the trick.
            below = [
                c for c in suit_cards
                if card_rank_in_context(c, trump, led_suit) < current_win_rank
            ]
            if below:
                # Play the highest card that stays below declarer (dumps danger safely)
                return _highest_in_context(below, trump, led_suit)
            # All our suit cards beat declarer — play lowest to waste as little as possible
            return _lowest_in_context(suit_cards, trump, led_suit)
        else:
            # Co-opponent (partner) is winning — dump our most dangerous (highest) card,
            # but only if we can't beat them (overtaking would hand the trick to no one useful).
            beaters = [
                c for c in suit_cards
                if card_rank_in_context(c, trump, led_suit) > current_win_rank
            ]
            non_beaters = [c for c in suit_cards if c not in beaters]
            if non_beaters:
                # Can't beat partner anyway — safely dump our highest (most dangerous)
                return _highest_in_context(non_beaters, trump, led_suit)
            # All cards beat partner — play lowest to avoid stealing the trick from them
            return _lowest_in_context(suit_cards, trump, led_suit)

    # ── Void in led suit: discard most dangerous card ─────────────────────────
    # Never play the joker (it always wins); discard highest non-joker instead
    non_joker = [c for c in legal if not c.is_joker()]
    if non_joker:
        return max(non_joker, key=lambda c: c.rank.value)
    return JOKER  # stuck


# ── Helper functions ──────────────────────────────────────────────────────────

def _highest_in_context(cards: list[Card], trump: Suit, led_suit: Suit) -> Card:
    return max(cards, key=lambda c: card_rank_in_context(c, trump, led_suit))


def _lowest_in_context(cards: list[Card], trump: Suit, led_suit: Suit) -> Card:
    return min(cards, key=lambda c: card_rank_in_context(c, trump, led_suit))


def _cheapest_discard(cards: list[Card], trump: Suit) -> Card:
    """Return the lowest-value card for discarding (no suit context)."""
    non_joker = [c for c in cards if not c.is_joker()]
    if not non_joker:
        return JOKER
    # Prefer to discard non-trump; among same group, lowest rank
    def discard_key(c):
        is_trump = c.effective_suit(trump) == trump
        return (is_trump, c.rank.value if c.rank else 0)
    return min(non_joker, key=discard_key)


def _is_definite_winner(
    card: Card, trump: Suit, hand: list[Card], played_cards: set[Card]
) -> bool:
    """
    True if this card is guaranteed to win its trick based on known information
    (our hand + cards already played in previous tricks).
    A card is a definite winner if no unplayed, unknown card can beat it.
    """
    if card.is_joker():
        return True

    suit = card.effective_suit(trump)
    if suit is None:
        return False  # NT joker edge-case; treat as not-a-winner for leading

    my_rank = card_rank_in_context(card, trump, suit)

    for other in _ALL_CARDS:
        if other == card:
            continue
        if other in played_cards:
            continue
        if other in hand:
            continue
        if other.effective_suit(trump) != suit:
            continue
        if card_rank_in_context(other, trump, suit) > my_rank:
            return False  # a higher card is still outstanding (unknown location)

    return True


def _outstanding_trump(
    trump: Suit, hand_trump: list[Card], played_cards: set[Card]
) -> list[Card]:
    """Return trump cards not yet played and not in our hand (still outstanding)."""
    hand_set = set(hand_trump)
    return [
        c for c in _ALL_CARDS
        if c.effective_suit(trump) == trump
        and c not in played_cards
        and c not in hand_set
    ]


def _group_by_effective_suit(cards: list[Card], trump: Suit) -> dict[Suit, list[Card]]:
    """Group cards by effective suit, dropping cards with no suit (NT joker)."""
    groups: dict[Suit, list[Card]] = {}
    for c in cards:
        s = c.effective_suit(trump)
        if s is not None:
            groups.setdefault(s, []).append(c)
    return groups
