"""
In-memory global GameState for the 500 debug webapp.

Phases: IDLE → BIDDING → KITTY → PLAYING → FINISHED
"""
from __future__ import annotations
import random
from typing import Optional
from collections import Counter

from ..game.cards import Card, Suit, JOKER
from ..game.deck import deal
from ..game.bidding import Bid, BidSuit, Contract, NULLO, DOUBLE_NULLO, all_bids
from ..game.tricks import (
    legal_plays, play_order, winning_seat, get_led_suit,
    NORTH, EAST, SOUTH, WEST,
)


# ── Bid parsing helpers ───────────────────────────────────────────────────────

def _parse_bid(bid_str: str) -> Optional[Bid]:
    """
    Parse a bid string into a Bid object, or return None for "PASS".

    Accepted formats:
      "PASS"           → None
      "NULLO"          → NULLO constant
      "DOUBLE_NULLO"   → DOUBLE_NULLO constant
      "6S","7H","8NT"  → Bid(tricks, suit)
    """
    s = bid_str.strip().upper()
    if s == "PASS":
        return None
    if s == "NULLO":
        return NULLO
    if s == "DOUBLE_NULLO":
        return DOUBLE_NULLO

    # Expect format like "7H", "10NT", "6S"
    suit_map = {
        "S": BidSuit.SPADES,
        "C": BidSuit.CLUBS,
        "H": BidSuit.HEARTS,
        "D": BidSuit.DIAMONDS,
        "NT": BidSuit.NO_TRUMP,
    }
    for suffix, bid_suit in suit_map.items():
        if s.endswith(suffix):
            tricks_str = s[: -len(suffix)]
            try:
                tricks = int(tricks_str)
            except ValueError:
                raise ValueError(f"Invalid bid: {bid_str!r}")
            if tricks < 6 or tricks > 11:
                raise ValueError(f"Tricks must be 6-11, got {tricks}")
            return Bid(tricks=tricks, suit=bid_suit)

    raise ValueError(f"Unrecognised bid: {bid_str!r}")


def _bid_beats(new_bid: Bid, current_highest: Optional[Bid]) -> bool:
    """True if new_bid is higher in value than current_highest (or no bid yet)."""
    if current_highest is None:
        return True
    # Same point value: Double Nullo beats regular bids
    if new_bid.point_value == current_highest.point_value:
        return new_bid.is_double_nullo and not current_highest.is_double_nullo
    return new_bid.point_value > current_highest.point_value


# ── Card serialisation ────────────────────────────────────────────────────────

def card_to_dict(card: Card) -> dict:
    if card.is_joker():
        return {"rank": None, "suit": None, "id": "Joker"}
    rank_str = {
        3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8",
        9: "9", 10: "10", 11: "J", 12: "Q", 13: "K", 14: "A",
    }[card.rank.value]
    return {"rank": rank_str, "suit": card.suit.value, "id": repr(card)}


def parse_card_id(card_id: str, pool: list[Card]) -> Card:
    """Find the Card object matching card_id in pool; raise if not found."""
    for c in pool:
        if repr(c) == card_id:
            return c
    raise ValueError(f"Card {card_id!r} not found in pool")


# ── Auto-suit for Joker led in NT ─────────────────────────────────────────────

def _most_common_suit(hand: list[Card]) -> Suit:
    """Return the plain suit with the most cards remaining (for Joker NT auto-suit)."""
    counts: Counter = Counter()
    for c in hand:
        if not c.is_joker() and c.suit in (Suit.SPADES, Suit.CLUBS, Suit.HEARTS, Suit.DIAMONDS):
            counts[c.suit] += 1
    if not counts:
        return Suit.SPADES  # fallback
    return counts.most_common(1)[0][0]


# ── GameState ─────────────────────────────────────────────────────────────────

class GameState:
    """
    All mutable state for one game session.  One global instance lives in routes.py.
    """

    def __init__(self) -> None:
        self.phase: str = "IDLE"

        # Cards
        self.hands: list[list[Card]] = [[], [], [], []]
        self.kitty: list[Card] = []
        self.kitty_visible: bool = False  # True during KITTY phase only

        # Bidding
        self.bids: list[tuple[int, Optional[Bid]]] = []  # (seat, bid|None)
        self.contract: Optional[Contract] = None
        self.current_bidder: int = NORTH  # seat 0 bids first
        self.highest_bid: Optional[Bid] = None
        self.highest_bidder: Optional[int] = None
        # (one-round bidding: no pass_count needed)

        # Tricks
        self.current_leader: int = SOUTH  # updated once contract known
        self.current_trick: list[tuple[int, Card]] = []  # (seat, card)
        self.tricks_history: list[dict] = []
        self.declarer_tricks: int = 0
        self.opponent_tricks: int = 0

        # Extra bookkeeping
        self.trick_just_completed: bool = False
        self.last_trick_winner: Optional[int] = None
        self.nt_joker_suit: Optional[Suit] = None  # declared suit when joker led in NT

        # Kitty cards given to declarer (for highlighting in UI)
        self.kitty_card_ids: list[str] = []

        # Scores (computed at game end)
        self.declarer_score: Optional[int] = None
        self.opponent_score: Optional[int] = None

        # Played cards as Card objects (needed by ISMCTS / heuristic)
        self.played_cards: set[Card] = set()

        # Random number generator shared across the session
        self.rng: random.Random = random.Random()

    # ── Deal ─────────────────────────────────────────────────────────────────

    def new_deal(self) -> None:
        hands, kitty = deal()
        self.hands = [list(h) for h in hands]
        self.kitty = list(kitty)
        self.kitty_visible = False
        self.bids = []
        self.contract = None
        self.current_bidder = NORTH
        self.highest_bid = None
        self.highest_bidder = None
        self.current_leader = SOUTH
        self.current_trick = []
        self.tricks_history = []
        self.declarer_tricks = 0
        self.opponent_tricks = 0
        self.trick_just_completed = False
        self.last_trick_winner = None
        self.nt_joker_suit = None
        self.kitty_card_ids = []
        self.declarer_score = None
        self.opponent_score = None
        self.played_cards = set()
        self.rng = random.Random()
        self.phase = "BIDDING"

    # ── Bidding ───────────────────────────────────────────────────────────────

    def place_bid(self, seat: int, bid_str: str) -> str:
        """
        Process one bid action.  Returns a status message.
        Raises ValueError on invalid input.

        One-round bidding: each of the 4 players bids exactly once (a valid
        higher bid or PASS).  After all 4 have bid, the highest bid wins.
        If all four pass, the hand is redealt.
        """
        if self.phase != "BIDDING":
            raise ValueError(f"Not in BIDDING phase (current: {self.phase})")
        if seat != self.current_bidder:
            raise ValueError(f"Not seat {seat}'s turn; expected {self.current_bidder}")
        if any(s == seat for s, _ in self.bids):
            raise ValueError(f"Seat {seat} has already bid this round")

        bid = _parse_bid(bid_str)

        if bid is not None:
            if not _bid_beats(bid, self.highest_bid):
                raise ValueError(
                    f"Bid {bid!r} does not beat current highest {self.highest_bid!r}"
                )
            # Double Nullo is only legal if your partner has already bid Nullo
            if bid.is_double_nullo:
                partner = (seat + 2) % 4
                partner_bid = next((b for s, b in self.bids if s == partner), None)
                if partner_bid != NULLO:
                    raise ValueError(
                        "Double Nullo is only valid if your partner has already bid Nullo"
                    )
            self.bids.append((seat, bid))
            self.highest_bid = bid
            self.highest_bidder = seat
        else:
            # Pass
            self.bids.append((seat, None))

        # Advance to next bidder
        self.current_bidder = (seat + 1) % 4

        # One round complete: all 4 players have bid
        if len(self.bids) == 4:
            if self.highest_bid is None:
                self.new_deal()
                return "All passed — redealing"
            self._resolve_bidding()
            seat_names = {0: "North", 1: "East", 2: "South", 3: "West"}
            return (
                f"Bidding over. {seat_names[self.highest_bidder]} won "
                f"with {self.highest_bid!r}"
            )

        return f"Bid accepted. Next bidder: {self.current_bidder}"

    def _resolve_bidding(self) -> None:
        """Bidding has ended.  Set contract, give kitty to winner."""
        declarer = self.highest_bidder
        self.contract = Contract(bid=self.highest_bid, declarer=declarer)
        # Record which card IDs came from the kitty (for UI highlighting)
        self.kitty_card_ids = [repr(c) for c in self.kitty]
        # Give kitty to declarer
        self.hands[declarer].extend(self.kitty)
        self.kitty_visible = True
        self.phase = "KITTY"

    # ── Kitty discard ─────────────────────────────────────────────────────────

    def discard(self, seat: int, card_ids: list[str]) -> str:
        if self.phase != "KITTY":
            raise ValueError(f"Not in KITTY phase (current: {self.phase})")
        if seat != self.contract.declarer:
            raise ValueError(f"Only the declarer (seat {self.contract.declarer}) may discard")
        if len(card_ids) != 3:
            raise ValueError("Must discard exactly 3 cards")

        hand = self.hands[seat]
        to_discard: list[Card] = []
        for cid in card_ids:
            card = parse_card_id(cid, hand)
            if card in to_discard:
                raise ValueError(f"Duplicate card in discard: {cid!r}")
            to_discard.append(card)

        for card in to_discard:
            hand.remove(card)

        # Kitty is now gone from view
        self.kitty = []
        self.kitty_visible = False

        # Declarer leads first trick
        self.current_leader = self.contract.declarer
        self.current_trick = []
        self.phase = "PLAYING"
        return "Discard accepted. Game started."

    # ── Playing ───────────────────────────────────────────────────────────────

    def _active_seats(self) -> tuple[int, ...]:
        return self.contract.active_seats if self.contract else (0, 1, 2, 3)

    def _trick_play_order(self) -> list[int]:
        return play_order(self.current_leader, self._active_seats())

    def whose_turn_to_play(self) -> Optional[int]:
        if self.phase != "PLAYING":
            return None
        order = self._trick_play_order()
        played = len(self.current_trick)
        if played >= len(order):
            return None  # trick just finished, waiting for resolution
        return order[played]

    def _get_led_suit_for_current_trick(self) -> Optional[Suit]:
        """Return the effective led suit for the current (in-progress) trick."""
        if not self.current_trick:
            return None
        _, lead_card = self.current_trick[0]
        trump = self.contract.trump or Suit.NO_TRUMP
        if lead_card.is_joker() and trump == Suit.NO_TRUMP:
            return self.nt_joker_suit  # may be None if not yet declared
        eff = lead_card.effective_suit(trump)
        return eff

    def legal_plays_for(self, seat: int) -> list[Card]:
        """Return legal cards for the given seat right now."""
        if self.phase != "PLAYING":
            return []
        if self.whose_turn_to_play() != seat:
            return []
        trump = self.contract.trump or Suit.NO_TRUMP
        led_suit = self._get_led_suit_for_current_trick()
        return legal_plays(self.hands[seat], led_suit, trump)

    def play_card(self, seat: int, card_id: str) -> str:
        if self.phase != "PLAYING":
            raise ValueError(f"Not in PLAYING phase (current: {self.phase})")

        expected = self.whose_turn_to_play()
        if expected is None:
            raise ValueError("No one expected to play right now")
        if seat != expected:
            raise ValueError(f"Not seat {seat}'s turn; expected {expected}")

        hand = self.hands[seat]
        card = parse_card_id(card_id, hand)

        trump = self.contract.trump or Suit.NO_TRUMP
        led_suit = self._get_led_suit_for_current_trick()

        if not is_legal_play_check(card, hand, led_suit, trump):
            raise ValueError(f"Card {card_id!r} is not a legal play")

        # Handle Joker led in NT — auto-assign suit
        is_lead = (len(self.current_trick) == 0)
        if is_lead and card.is_joker() and trump == Suit.NO_TRUMP:
            self.nt_joker_suit = _most_common_suit(
                [c for c in hand if c != card]
            )

        hand.remove(card)
        self.current_trick.append((seat, card))

        self.trick_just_completed = False

        # Check if trick is complete
        order = self._trick_play_order()
        if len(self.current_trick) == len(order):
            self._resolve_trick()
            return "Trick complete"

        return "Card played"

    def _resolve_trick(self) -> None:
        """Called when all seats have played to the current trick."""
        trump = self.contract.trump or Suit.NO_TRUMP

        # Led suit
        _, lead_card = self.current_trick[0]
        if lead_card.is_joker() and trump == Suit.NO_TRUMP:
            led_suit = self.nt_joker_suit or Suit.SPADES
        else:
            led_suit = lead_card.effective_suit(trump)

        play_order_seats = self._trick_play_order()
        trick_cards = [c for _, c in self.current_trick]

        winner = winning_seat(trick_cards, trump, led_suit, play_order_seats)

        declarer_won = self.contract.is_declarer_side(winner)
        if declarer_won:
            self.declarer_tricks += 1
        else:
            self.opponent_tricks += 1

        self.tricks_history.append({
            "cards": [card_to_dict(c) for c in trick_cards],
            "seats": play_order_seats,
            "winner": winner,
            "declarer_won": declarer_won,
        })

        self.last_trick_winner = winner
        self.trick_just_completed = True
        self.nt_joker_suit = None  # reset for next trick
        self.played_cards.update(trick_cards)

        # Advance
        self.current_leader = winner
        self.current_trick = []

        # Check game over
        total_tricks = self.declarer_tricks + self.opponent_tricks
        total_expected = len(self._active_seats()) * 11 // len(self._active_seats())
        # 11 tricks total in 4-player, fewer in 3-player nullo
        # Each player plays once per trick; total tricks = 11
        if total_tricks >= 11:
            self.phase = "FINISHED"
            self._compute_scores()

    def _compute_scores(self) -> None:
        """
        500 scoring rules:
        - Declaring side: +bid_points if made, -bid_points if not made.
          No bonus for over-tricks.
        - Opponents: +10 points per trick won (always, regardless of contract result).
        """
        if not self.contract:
            return
        made = self.contract.made_contract(self.declarer_tricks)
        bid_pts = self.contract.bid.point_value
        self.declarer_score = bid_pts if made else -bid_pts
        self.opponent_score = self.opponent_tricks * 10

    # ── Bot play (ISMCTS) ────────────────────────────────────────────────────

    # Seat 2 (South) is the human; all others are bots
    HUMAN_SEAT: int = SOUTH

    def advance_bots(self) -> None:
        """
        Auto-play all bot seats until it's the human's turn or the game ends.
        Called after the human plays a card (or at game start if bots lead first).
        """
        while self.phase == "PLAYING":
            seat = self.whose_turn_to_play()
            if seat is None or seat == self.HUMAN_SEAT:
                break
            card = self._bot_choose_card(seat)
            self.play_card(seat, repr(card))

    def _bot_choose_card(self, seat: int) -> Card:
        """Choose a card for a bot seat using ISMCTS with heuristic fallback."""
        from backend.solver.ismcts import run_ismcts
        from backend.solver.heuristic import play_card as heuristic_play

        trump = self.contract.trump or Suit.NO_TRUMP
        trick_cards = [c for _, c in self.current_trick]
        trick_seats  = [s for s, _ in self.current_trick]
        tricks_done  = len(self.tricks_history)

        try:
            return run_ismcts(
                root_seat=seat,
                root_hand=list(self.hands[seat]),
                played_cards=set(self.played_cards),
                trick_so_far=trick_cards,
                trick_seats_so_far=trick_seats,
                contract=self.contract,
                trump=trump,
                leader=self.current_leader,
                dec_tricks_so_far=self.declarer_tricks,
                tricks_done=tricks_done,
                rng=self.rng,
                time_budget_s=0.5,
            )
        except Exception:
            # Heuristic fallback — never let a bot crash the game
            led = self._get_led_suit_for_current_trick()
            return heuristic_play(
                seat=seat,
                hand=self.hands[seat],
                trick_so_far=trick_cards,
                leader_seat=self.current_leader,
                led_suit=led,
                trump=trump,
                contract=self.contract,
                played_cards=self.played_cards,
                rng=self.rng,
            )

    # ── State serialisation ───────────────────────────────────────────────────

    def to_response(self) -> dict:
        """Build the full state dict that maps to GameStateResponse."""

        # Whose turn
        if self.phase == "BIDDING":
            whose_turn = self.current_bidder
        elif self.phase == "KITTY":
            whose_turn = self.contract.declarer if self.contract else None
        elif self.phase == "PLAYING":
            whose_turn = self.whose_turn_to_play()
        else:
            whose_turn = None

        # Legal plays
        legal: list[dict] = []
        if self.phase == "PLAYING" and whose_turn is not None:
            legal = [card_to_dict(c) for c in self.legal_plays_for(whose_turn)]

        # Contract info
        contract_info = None
        if self.contract:
            c = self.contract
            contract_info = {
                "bid": repr(c.bid),
                "declarer": c.declarer,
                "partner": c.partner,
                "trump": c.trump.value if c.trump else None,
                "active_seats": list(c.active_seats),
                "tricks_needed": c.tricks_needed(),
                "point_value": c.bid.point_value,
            }

        # Current trick
        current_trick_out = [
            {"seat": seat, "card": card_to_dict(card)}
            for seat, card in self.current_trick
        ]

        # Kitty — visible only during KITTY phase
        kitty_out = [card_to_dict(c) for c in self.kitty] if self.kitty_visible else []

        # Bid history
        bids_out = [
            {"seat": s, "bid": repr(b) if b else "Pass"}
            for s, b in self.bids
        ]

        # Message
        msg = self._status_message(whose_turn)

        return {
            "phase": self.phase,
            "hands": [[card_to_dict(c) for c in h] for h in self.hands],
            "kitty": kitty_out,
            "bids": bids_out,
            "contract": contract_info,
            "current_bidder": self.current_bidder if self.phase == "BIDDING" else None,
            "highest_bid": repr(self.highest_bid) if self.highest_bid else None,
            "highest_bidder": self.highest_bidder,
            "current_leader": self.current_leader if self.phase == "PLAYING" else None,
            "current_trick": current_trick_out,
            "tricks_history": self.tricks_history,
            "declarer_tricks": self.declarer_tricks,
            "opponent_tricks": self.opponent_tricks,
            "whose_turn": whose_turn,
            "legal_plays": legal,
            "trick_just_completed": self.trick_just_completed,
            "last_trick_winner": self.last_trick_winner,
            "kitty_card_ids": self.kitty_card_ids if self.phase == "KITTY" else [],
            "declarer_score": self.declarer_score,
            "opponent_score": self.opponent_score,
            "message": msg,
        }

    def _status_message(self, whose_turn: Optional[int]) -> str:
        seat_names = {0: "North", 1: "East", 2: "South", 3: "West"}
        if self.phase == "IDLE":
            return "Click 'Deal New Hand' to start."
        if self.phase == "BIDDING":
            cur = seat_names.get(self.current_bidder, str(self.current_bidder))
            high = f" (current: {self.highest_bid!r})" if self.highest_bid else ""
            return f"Bidding — {cur}'s turn{high}"
        if self.phase == "KITTY":
            dec = seat_names.get(self.contract.declarer, "?")
            return f"{dec} picks up kitty and discards 3 cards"
        if self.phase == "PLAYING":
            if self.trick_just_completed and self.last_trick_winner is not None:
                winner = seat_names.get(self.last_trick_winner, "?")
                return f"{winner} won the last trick. Declarer: {self.declarer_tricks}, Opponents: {self.opponent_tricks}"
            if whose_turn is not None:
                name = seat_names.get(whose_turn, str(whose_turn))
                return f"Playing — {name}'s turn to play"
            return "Playing"
        if self.phase == "FINISHED":
            c = self.contract
            made = c.made_contract(self.declarer_tricks) if c else False
            dec = seat_names.get(c.declarer, "?") if c else "?"
            result = "MADE" if made else "WENT DOWN"
            return (
                f"Game over — {dec} {result} {c.bid!r}. "
                f"Declarer tricks: {self.declarer_tricks}, "
                f"Opponent tricks: {self.opponent_tricks}"
            )
        return ""


# ── Standalone helper (imported by routes) ───────────────────────────────────

def is_legal_play_check(card: Card, hand: list[Card], led_suit, trump: Suit) -> bool:
    """Thin wrapper so routes.py doesn't need to import from tricks directly."""
    from ..game.tricks import is_legal_play
    return is_legal_play(card, hand, led_suit, trump)
