"""
Game state representation for SO-ISMCTS tree traversal, plus the world sampler.

Public API
----------
sample_world(root_seat, root_hand, played_cards, trick_so_far,
             trick_seats_so_far, contract, rng) -> list[list[Card]]

ISMCTSState   – mutable state that advances as cards are applied
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from backend.game.cards import Card, Suit
from backend.game.bidding import Contract
from backend.game.deck import build_deck
from backend.game.tricks import legal_plays, play_order, winning_seat

_DECK: list[Card] = build_deck()
_PLAIN_SUITS = [Suit.SPADES, Suit.CLUBS, Suit.HEARTS, Suit.DIAMONDS]


# ── World sampler ─────────────────────────────────────────────────────────────

def sample_world(
    root_seat: int,
    root_hand: list[Card],
    played_cards: set[Card],
    trick_so_far: list[Card],
    trick_seats_so_far: list[int],
    contract: Contract,
    rng: random.Random,
) -> list[list[Card]]:
    """
    Distribute unseen cards to non-root seats consistently with public information.

    root_hand          : cards currently held by root_seat (already played cards removed)
    played_cards       : cards played in *completed* tricks (public knowledge)
    trick_so_far       : cards played so far in the current in-progress trick
    trick_seats_so_far : which seat played each card in trick_so_far (parallel list)

    The 3 discarded kitty cards are never assigned to anyone — they fall out
    naturally because each non-root seat gets exactly their expected hand size,
    leaving (unseen − distributed) = 3 cards un-assigned.
    """
    known = set(root_hand) | played_cards | set(trick_so_far)
    unseen = [c for c in _DECK if c not in known]
    rng.shuffle(unseen)

    # root_hand size == 11 − tricks_completed (same for every active seat)
    expected_size = len(root_hand)
    played_this_trick = set(trick_seats_so_far)

    seats_to_fill: list[tuple[int, int]] = []
    for seat in range(4):
        if seat == root_seat:
            continue
        sitting_out = (
            contract.bid.is_nullo
            and not contract.bid.is_double_nullo
            and seat == contract.partner
        )
        if sitting_out:
            # Partner in regular Nullo: holds all 11 cards, never plays
            seats_to_fill.append((seat, 11))
        elif seat in contract.active_seats:
            size = expected_size - (1 if seat in played_this_trick else 0)
            seats_to_fill.append((seat, max(0, size)))

    hands: list[list[Card]] = [[] for _ in range(4)]
    hands[root_seat] = list(root_hand)

    idx = 0
    for seat, size in seats_to_fill:
        hands[seat] = unseen[idx : idx + size]
        idx += size
    # unseen[idx:] ≈ 3 discarded kitty cards — ignored

    return hands


# ── Mutable game state ────────────────────────────────────────────────────────

@dataclass
class ISMCTSState:
    """
    Mutable game state for a single determinisation inside the ISMCTS tree.
    Advance it by calling apply(); query reward() at terminal.
    """
    hands:       list[list[Card]]   # hands[seat] — mutated as cards are played
    contract:    Contract
    trump:       Suit               # Suit.NO_TRUMP for nullo / NT
    leader:      int                # who leads the current trick
    tricks_done: int                # completed tricks (0–11)
    dec_tricks:  int                # tricks won by declaring side so far
    trick:       list[Card]  = field(default_factory=list)  # current trick cards
    played:      set[Card]   = field(default_factory=set)   # completed-trick cards
    _order:      list[int]   = field(default_factory=list)  # play order this trick

    def __post_init__(self) -> None:
        if not self._order:
            self._order = play_order(self.leader, self.contract.active_seats)

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def current_seat(self) -> int:
        return self._order[len(self.trick)]

    @property
    def led_suit(self) -> Optional[Suit]:
        if not self.trick:
            return None
        lead = self.trick[0]
        if lead.is_joker() and self.trump == Suit.NO_TRUMP:
            return _nt_joker_led_suit(self.hands[self._order[0]])
        return lead.effective_suit(self.trump)

    def legal(self) -> list[Card]:
        return legal_plays(self.hands[self.current_seat], self.led_suit, self.trump)

    def is_terminal(self) -> bool:
        return self.tricks_done == 11

    # ── Mutation ──────────────────────────────────────────────────────────────

    def apply(self, card: Card) -> None:
        """Play card for the current seat; resolve trick if complete."""
        seat = self.current_seat
        self.hands[seat].remove(card)
        self.trick.append(card)

        if len(self.trick) == len(self._order):
            # Trick complete — determine winner and reset
            led = self.led_suit or Suit.SPADES
            winner = winning_seat(self.trick, self.trump, led, self._order)
            if self.contract.is_declarer_side(winner):
                self.dec_tricks += 1
            self.played |= set(self.trick)
            self.tricks_done += 1
            self.leader = winner
            self.trick = []
            self._order = play_order(winner, self.contract.active_seats)

    # ── Reward ────────────────────────────────────────────────────────────────

    def reward(self, root_seat: int) -> float:
        """
        Normalised reward in [0, 1] from root_seat's perspective.
        Nullo: declaring side wants fewer tricks → invert the fraction.
        """
        is_nullo = self.contract.bid.is_nullo or self.contract.bid.is_double_nullo
        dec_score = (11 - self.dec_tricks) / 11 if is_nullo else self.dec_tricks / 11
        if self.contract.is_declarer_side(root_seat):
            return dec_score
        return 1.0 - dec_score

    # ── Clone ─────────────────────────────────────────────────────────────────

    def clone(self) -> ISMCTSState:
        return ISMCTSState(
            hands=[list(h) for h in self.hands],
            contract=self.contract,
            trump=self.trump,
            leader=self.leader,
            tricks_done=self.tricks_done,
            dec_tricks=self.dec_tricks,
            trick=list(self.trick),
            played=set(self.played),
            _order=list(self._order),
        )


# ── NT joker helper ───────────────────────────────────────────────────────────

def _nt_joker_led_suit(leader_hand: list[Card]) -> Suit:
    """Declare the suit with most remaining cards in leader's hand (NT joker lead)."""
    counts = {s: 0 for s in _PLAIN_SUITS}
    for c in leader_hand:
        if c.suit in counts:
            counts[c.suit] += 1
    return max(counts, key=counts.__getitem__) if any(counts.values()) else Suit.SPADES
