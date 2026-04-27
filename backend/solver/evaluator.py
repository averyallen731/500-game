"""
Bid evaluator: samples random deals, simulates each with the heuristic policy,
and returns expected trick distributions + optimal bid recommendation.

Public API
----------
evaluate_hand(hand, declarer, n_samples) -> BidAdvice
"""

import random
import statistics
from dataclasses import dataclass, field

from backend.game.cards import Card, Suit
from backend.game.bidding import Contract, Bid, BidSuit, _BASE_POINTS
from backend.game.tricks import play_order, winning_seat, legal_plays
from backend.game.hand import best_kitty_discard
from backend.solver.sampler import sample_remaining
from backend.solver.heuristic import play_card

_PLAIN_SUITS = [Suit.SPADES, Suit.CLUBS, Suit.HEARTS, Suit.DIAMONDS]


# ── Result dataclasses ────────────────────────────────────────────────────────

@dataclass
class TrumpEval:
    """Simulation results for one trump choice."""
    trump_name: str           # "S" | "C" | "H" | "D" | "NT" | "NULLO"
    avg_tricks: float         # mean tricks won by declaring side
    std_dev: float
    histogram: list[int]      # histogram[k] = # samples where declaring side won k tricks
    skipped: bool = False     # True if smart pruning skipped this trump


@dataclass
class BidAdvice:
    """Full bid analysis for a hand."""
    evaluations: dict[str, TrumpEval]   # keyed by trump_name
    optimal_bid: str                     # e.g. "8H", "7NT", "NULLO"
    optimal_ev: float                    # expected points for the optimal bid
    n_samples: int


# ── Trump choices ─────────────────────────────────────────────────────────────

# (trump_name, bid_suit_enum, game_suit_or_None, is_nullo)
_TRUMP_CHOICES = [
    ("S",     BidSuit.SPADES,    Suit.SPADES,    False),
    ("C",     BidSuit.CLUBS,     Suit.CLUBS,     False),
    ("H",     BidSuit.HEARTS,    Suit.HEARTS,    False),
    ("D",     BidSuit.DIAMONDS,  Suit.DIAMONDS,  False),
    ("NT",    BidSuit.NO_TRUMP,  Suit.NO_TRUMP,  False),
    ("NULLO", BidSuit.NULLO,     None,           True),
]


# ── Public API ────────────────────────────────────────────────────────────────

def evaluate_hand(
    hand: list[Card],
    declarer: int = 2,
    n_samples: int = 200,
    rng: random.Random | None = None,
) -> BidAdvice:
    """
    Simulate n_samples random deals for each of 6 trump choices and return
    expected trick distributions plus the highest-EV bid recommendation.

    hand     : the declarer's 11-card hand (before picking up kitty)
    declarer : seat number (0=N, 1=E, 2=S, 3=W); default 2 (South / user)
    n_samples: deals to simulate per trump choice
    rng      : optional seeded RNG for reproducibility
    """
    if rng is None:
        rng = random.Random()

    evaluations: dict[str, TrumpEval] = {}

    for trump_name, bid_suit, trump_suit, is_nullo in _TRUMP_CHOICES:
        if _should_skip(hand, trump_suit, is_nullo):
            evaluations[trump_name] = TrumpEval(trump_name, 0.0, 0.0, [0] * 12, skipped=True)
            continue

        # Effective trump for trick resolution (NO_TRUMP for nullo)
        trump = trump_suit if trump_suit is not None else Suit.NO_TRUMP

        # Dummy contract — level 6 is fine; we only care about active_seats/is_nullo
        contract = Contract(bid=Bid(tricks=6, suit=bid_suit), declarer=declarer)

        trick_counts: list[int] = []
        for _ in range(n_samples):
            hands, kitty = sample_remaining(hand, declarer, rng)

            # Declarer picks up kitty and makes an optimal greedy discard
            hand_14 = hands[declarer] + kitty
            kept, _ = best_kitty_discard(hand_14, trump, nullo=is_nullo)
            hands[declarer] = kept

            tricks = _simulate_game(hands, contract, trump, rng)
            trick_counts.append(tricks)

        avg = statistics.mean(trick_counts)
        std = statistics.stdev(trick_counts) if len(trick_counts) > 1 else 0.0
        hist = [trick_counts.count(k) for k in range(12)]
        evaluations[trump_name] = TrumpEval(trump_name, avg, std, hist)

    optimal_bid, optimal_ev = _best_bid(evaluations)
    return BidAdvice(evaluations, optimal_bid, optimal_ev, n_samples)


# ── Simulation ────────────────────────────────────────────────────────────────

def _simulate_game(
    hands: list[list[Card]],
    contract: Contract,
    trump: Suit,
    rng: random.Random,
) -> int:
    """
    Play out a full 11-trick game using the heuristic policy.
    Returns the number of tricks won by the declaring side.
    """
    hands_copy = [list(h) for h in hands]
    played_cards: set[Card] = set()
    leader = contract.declarer
    active = contract.active_seats
    declarer_tricks = 0

    for _ in range(11):
        trick_cards: list[Card] = []
        playing_order = play_order(leader, active)
        led_suit: Suit | None = None

        for seat in playing_order:
            card = play_card(
                seat=seat,
                hand=hands_copy[seat],
                trick_so_far=trick_cards,
                leader_seat=leader,
                led_suit=led_suit,
                trump=trump,
                contract=contract,
                played_cards=played_cards,
                rng=rng,
            )
            hands_copy[seat].remove(card)
            trick_cards.append(card)
            played_cards.add(card)

            # Set led_suit once the leader plays
            if led_suit is None:
                if card.is_joker() and trump == Suit.NO_TRUMP:
                    # Joker leads in NT/nullo: declare the suit with most remaining cards
                    suit_counts: dict[Suit, int] = {}
                    for c in hands_copy[seat]:
                        if not c.is_joker() and c.suit is not None:
                            suit_counts[c.suit] = suit_counts.get(c.suit, 0) + 1
                    if suit_counts:
                        led_suit = max(suit_counts, key=suit_counts.get)
                    else:
                        led_suit = rng.choice(_PLAIN_SUITS)
                else:
                    eff = card.effective_suit(trump)
                    led_suit = eff if eff is not None else rng.choice(_PLAIN_SUITS)

        winner = winning_seat(trick_cards, trump, led_suit, playing_order)
        if contract.is_declarer_side(winner):
            declarer_tricks += 1
        leader = winner

    return declarer_tricks


# ── Smart pruning ─────────────────────────────────────────────────────────────

def _should_skip(hand: list[Card], trump_suit: Suit | None, is_nullo: bool) -> bool:
    """
    Return True if this trump choice is obviously not worth simulating.
    Keeps the evaluation fast without sacrificing meaningful options.
    """
    if is_nullo or trump_suit == Suit.NO_TRUMP:
        return False  # always evaluate NT and nullo

    # Skip suit-trump choices where we hold fewer than 3 cards in that suit
    trump_count = sum(1 for c in hand if c.effective_suit(trump_suit) == trump_suit)
    return trump_count < 3


# ── EV computation ────────────────────────────────────────────────────────────

def _best_bid(evaluations: dict[str, TrumpEval]) -> tuple[str, float]:
    """
    Find the bid with the highest expected value across all trump choices and levels.
    EV = P(making) × bid_pts − P(failing) × bid_pts
    """
    _SUIT_MAP = {
        "S": BidSuit.SPADES, "C": BidSuit.CLUBS,
        "H": BidSuit.HEARTS, "D": BidSuit.DIAMONDS,
        "NT": BidSuit.NO_TRUMP,
    }

    best_bid_str = "PASS"
    best_ev = 0.0  # PASS if no bid has positive EV

    for trump_name, result in evaluations.items():
        if result.skipped:
            continue

        n = sum(result.histogram)
        if n == 0:
            continue

        if trump_name == "NULLO":
            pts = 250
            pct_making = result.histogram[0] / n
            ev = pts * pct_making - pts * (1 - pct_making)
            if ev > best_ev:
                best_ev = ev
                best_bid_str = "NULLO"
        else:
            bid_suit = _SUIT_MAP[trump_name]
            for level in range(6, 12):
                pts = _BASE_POINTS[level][bid_suit]
                pct_making = sum(result.histogram[k] for k in range(level, 12)) / n
                ev = pts * pct_making - pts * (1 - pct_making)
                if ev > best_ev:
                    best_ev = ev
                    best_bid_str = f"{level}{trump_name}"

    return best_bid_str, best_ev
