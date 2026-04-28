"""
Phase 3 lead-strategy benchmark for 500.

Tests A (current baseline), G (aces from shortest suit), G+E (G + singleton-only probe),
and G+ (Avery's pure strategy: aces from shortest → singleton low → pull trump).

Runs 400 paired deals (same RNG seed per deal, both strategies see identical hands).
Reports avg tricks won by declaring side, delta vs baseline.

Run from project root:
    python -m scripts.bench_leads
"""
from __future__ import annotations

import copy
import random
import statistics
from typing import Callable

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.game.cards import Card, Suit, card_rank_in_context
from backend.game.deck import build_deck
from backend.game.tricks import legal_plays, play_order, winning_seat, winning_card_index
from backend.game.bidding import Contract, Bid, BidSuit
from backend.game.hand import best_kitty_discard
from backend.solver.sampler import sample_remaining
from backend.solver.heuristic import (
    play_card, _follow_make_tricks,
    _highest_in_context, _lowest_in_context,
    _is_definite_winner, _outstanding_trump,
    _group_by_effective_suit, _cheapest_discard,
    _ALL_CARDS,
)

_PLAIN_SUITS = [Suit.SPADES, Suit.CLUBS, Suit.HEARTS, Suit.DIAMONDS]


# ─────────────────────────────────────────────────────────────────────────────
# Strategy variants
# Each variant replaces ONLY the _lead_make_tricks function.
# _follow_make_tricks is shared (unchanged) for all variants.
# ─────────────────────────────────────────────────────────────────────────────

# ── Strategy A: Current baseline (original heuristic) ────────────────────────
def lead_A(seat, hand, legal, trump, contract, played_cards, rng):
    """Original: pull trump → cash winners (longest suit first) → top of longest side suit."""
    trump_in_hand = [c for c in legal if c.effective_suit(trump) == trump]
    non_trump = [c for c in legal if c.effective_suit(trump) != trump]

    # Pull trump first
    if trump != Suit.NO_TRUMP and trump_in_hand:
        outstanding = _outstanding_trump(trump, trump_in_hand, played_cards)
        if outstanding:
            return _highest_in_context(trump_in_hand, trump, trump)

    # Cash definite winners (longest suit first)
    winners = [c for c in legal if _is_definite_winner(c, trump, hand, played_cards)]
    if winners:
        return max(winners, key=lambda c: (
            len([x for x in hand if x.effective_suit(trump) == c.effective_suit(trump)]),
            card_rank_in_context(c, trump, c.effective_suit(trump) or trump),
        ))

    # Top of longest side suit
    if non_trump:
        groups = _group_by_effective_suit(non_trump, trump)
        if groups:
            longest = max(groups, key=lambda s: len(groups[s]))
            return _highest_in_context(groups[longest], trump, longest)

    if trump_in_hand:
        return _lowest_in_context(trump_in_hand, trump, trump)
    return rng.choice(legal)


# ── Strategy G: Aces from shortest suit first (probe likely-voided suits) ────
def lead_G(seat, hand, legal, trump, contract, played_cards, rng):
    """
    User-inspired: cash aces from SHORTEST suit first (probe where opponents are void),
    then lead low from short suits (partner ruff probe),
    then pull trump,
    then top of longest.
    """
    trump_in_hand = [c for c in legal if c.effective_suit(trump) == trump]
    non_trump = [c for c in legal if c.effective_suit(trump) != trump]

    # 1. Cash definite winners — from SHORTEST suit first (probe for voids)
    winners = [c for c in non_trump if _is_definite_winner(c, trump, hand, played_cards)]
    if winners:
        # Lead ace/winner from shortest suit (most likely to find a void in opponents)
        return min(winners, key=lambda c: (
            len([x for x in hand if x.effective_suit(trump) == c.effective_suit(trump)]),
            -card_rank_in_context(c, trump, c.effective_suit(trump) or trump),
        ))

    # 2. Short-suit probe: lead lowest from singletons OR doubletons (partner ruff)
    if non_trump and trump != Suit.NO_TRUMP:
        groups = _group_by_effective_suit(non_trump, trump)
        short_groups = {s: cards for s, cards in groups.items() if len(cards) <= 2}
        if short_groups:
            # Pick the shortest suit; break ties by lowest card
            shortest_suit = min(short_groups, key=lambda s: len(short_groups[s]))
            return _lowest_in_context(short_groups[shortest_suit], trump, shortest_suit)

    # 3. Pull trump
    if trump != Suit.NO_TRUMP and trump_in_hand:
        outstanding = _outstanding_trump(trump, trump_in_hand, played_cards)
        if outstanding:
            return _highest_in_context(trump_in_hand, trump, trump)

    # 4. Top of longest side suit
    if non_trump:
        groups = _group_by_effective_suit(non_trump, trump)
        if groups:
            longest = max(groups, key=lambda s: len(groups[s]))
            return _highest_in_context(groups[longest], trump, longest)

    if trump_in_hand:
        return _lowest_in_context(trump_in_hand, trump, trump)
    return rng.choice(legal)


# ── Strategy GE: G + singleton probe ONLY (no doubleton probes) ──────────────
def lead_GE(seat, hand, legal, trump, contract, played_cards, rng):
    """
    G variant: aces from shortest suit → SINGLETON probe only → pull trump → top of longest.
    """
    trump_in_hand = [c for c in legal if c.effective_suit(trump) == trump]
    non_trump = [c for c in legal if c.effective_suit(trump) != trump]

    # 1. Cash definite winners from shortest suit first
    winners = [c for c in non_trump if _is_definite_winner(c, trump, hand, played_cards)]
    if winners:
        return min(winners, key=lambda c: (
            len([x for x in hand if x.effective_suit(trump) == c.effective_suit(trump)]),
            -card_rank_in_context(c, trump, c.effective_suit(trump) or trump),
        ))

    # 2. Singleton probe only (no doubletons)
    if non_trump and trump != Suit.NO_TRUMP:
        groups = _group_by_effective_suit(non_trump, trump)
        singleton_groups = {s: cards for s, cards in groups.items() if len(cards) == 1}
        if singleton_groups:
            # Lead our singleton (partner may be able to ruff follow-ups)
            suit = next(iter(singleton_groups))
            return singleton_groups[suit][0]

    # 3. Pull trump
    if trump != Suit.NO_TRUMP and trump_in_hand:
        outstanding = _outstanding_trump(trump, trump_in_hand, played_cards)
        if outstanding:
            return _highest_in_context(trump_in_hand, trump, trump)

    # 4. Top of longest side suit
    if non_trump:
        groups = _group_by_effective_suit(non_trump, trump)
        if groups:
            longest = max(groups, key=lambda s: len(groups[s]))
            return _highest_in_context(groups[longest], trump, longest)

    if trump_in_hand:
        return _lowest_in_context(trump_in_hand, trump, trump)
    return rng.choice(legal)


# ── Strategy G+: Pure Avery strategy — aces shortest → singleton low → pull trump ──
def lead_Gplus(seat, hand, legal, trump, contract, played_cards, rng):
    """
    Avery's stated strategy:
    1. Lead offsuit aces (from shortest suit — probe for voids)
    2. Lead lowest from singletons only (partner ruff)
    3. Pull trump with highest trump
    4. Top of longest side suit
    (No doubleton probe; pull trump eagerly after aces)
    """
    trump_in_hand = [c for c in legal if c.effective_suit(trump) == trump]
    non_trump = [c for c in legal if c.effective_suit(trump) != trump]

    # 1. Cash aces (definite winners) from shortest non-trump suit
    winners = [c for c in non_trump if _is_definite_winner(c, trump, hand, played_cards)]
    if winners:
        return min(winners, key=lambda c: (
            len([x for x in hand if x.effective_suit(trump) == c.effective_suit(trump)]),
            -card_rank_in_context(c, trump, c.effective_suit(trump) or trump),
        ))

    # 2. Pull trump immediately if outstanding (before any probe)
    if trump != Suit.NO_TRUMP and trump_in_hand:
        outstanding = _outstanding_trump(trump, trump_in_hand, played_cards)
        if outstanding:
            return _highest_in_context(trump_in_hand, trump, trump)

    # 3. Singleton probe only (after trump is pulled)
    if non_trump:
        groups = _group_by_effective_suit(non_trump, trump)
        singleton_groups = {s: cards for s, cards in groups.items() if len(cards) == 1}
        if singleton_groups:
            suit = next(iter(singleton_groups))
            return singleton_groups[suit][0]

    # 4. Top of longest side suit
    if non_trump:
        groups = _group_by_effective_suit(non_trump, trump)
        if groups:
            longest = max(groups, key=lambda s: len(groups[s]))
            return _highest_in_context(groups[longest], trump, longest)

    if trump_in_hand:
        return _lowest_in_context(trump_in_hand, trump, trump)
    return rng.choice(legal)


# ─────────────────────────────────────────────────────────────────────────────
# Pluggable play_card factory
# ─────────────────────────────────────────────────────────────────────────────

def make_play_card(lead_fn):
    """Return a play_card function that uses lead_fn for make-tricks leads."""
    def _play_card(seat, hand, trick_so_far, leader_seat, led_suit, trump, contract, played_cards, rng):
        from backend.solver.heuristic import (
            _play_nullo, _play_nullo_defense, _play_make_tricks
        )
        legal = legal_plays(hand, led_suit, trump)
        if len(legal) == 1:
            return legal[0]

        is_nullo = contract.bid.is_nullo or contract.bid.is_double_nullo
        am_declarer_side = contract.is_declarer_side(seat)

        if is_nullo and am_declarer_side:
            return _play_nullo(seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, rng)
        if is_nullo and not am_declarer_side:
            return _play_nullo_defense(seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, rng)

        # Make-tricks: use custom lead
        if led_suit is None:
            return lead_fn(seat, hand, legal, trump, contract, played_cards, rng)
        return _follow_make_tricks(seat, hand, legal, trick_so_far, leader_seat, led_suit, trump, contract, rng)

    return _play_card


# ─────────────────────────────────────────────────────────────────────────────
# Simulation engine (mirrors evaluator._simulate_game but accepts play_card fn)
# ─────────────────────────────────────────────────────────────────────────────

def simulate_game(hands_in, contract, trump, rng, play_fn):
    hands = [list(h) for h in hands_in]
    played_cards: set[Card] = set()
    leader = contract.declarer
    active = contract.active_seats
    declarer_tricks = 0

    for _ in range(11):
        trick_cards: list[Card] = []
        playing_order = play_order(leader, active)
        led_suit = None

        for seat in playing_order:
            card = play_fn(
                seat=seat, hand=hands[seat], trick_so_far=trick_cards,
                leader_seat=leader, led_suit=led_suit, trump=trump,
                contract=contract, played_cards=played_cards, rng=rng,
            )
            hands[seat].remove(card)
            trick_cards.append(card)
            played_cards.add(card)

            if led_suit is None:
                if card.is_joker() and trump == Suit.NO_TRUMP:
                    suit_counts: dict[Suit, int] = {}
                    for c in hands[seat]:
                        if not c.is_joker() and c.suit is not None:
                            suit_counts[c.suit] = suit_counts.get(c.suit, 0) + 1
                    led_suit = max(suit_counts, key=suit_counts.get) if suit_counts else Suit.SPADES
                else:
                    eff = card.effective_suit(trump)
                    led_suit = eff if eff is not None else Suit.SPADES

        winner = winning_seat(trick_cards, trump, led_suit, playing_order)
        if contract.is_declarer_side(winner):
            declarer_tricks += 1
        leader = winner

    return declarer_tricks


# ─────────────────────────────────────────────────────────────────────────────
# Paired benchmark
# ─────────────────────────────────────────────────────────────────────────────

STRATEGIES = {
    "A (baseline)": lead_A,
    "G (aces-shortest)": lead_G,
    "G+E (aces-shortest+singleton)": lead_GE,
    "G+ (aces→trump→singleton)": lead_Gplus,
}

N_DEALS = 400
DECLARER = 2
TRUMP_CHOICE = BidSuit.HEARTS   # Hearts is a representative suit trump
TRUMP_SUIT = Suit.HEARTS


def run_benchmark():
    rng_master = random.Random(42)
    deal_seeds = [rng_master.randint(0, 2**32) for _ in range(N_DEALS)]

    contract = Contract(bid=Bid(tricks=8, suit=TRUMP_CHOICE), declarer=DECLARER)

    results: dict[str, list[int]] = {name: [] for name in STRATEGIES}

    play_fns = {name: make_play_card(fn) for name, fn in STRATEGIES.items()}

    for i, seed in enumerate(deal_seeds):
        if (i + 1) % 100 == 0:
            print(f"  Deal {i+1}/{N_DEALS}…")

        # Generate ONE deal for this seed (used by all strategies)
        deal_rng = random.Random(seed)
        # Sample a fresh hand for the declarer seat
        from backend.solver.sampler import sample_remaining
        # We need a full deck deal — sample_remaining needs a known hand.
        # Use the full deck approach: deal 11 cards to seat 2, rest randomly.
        from backend.game.deck import build_deck
        from backend.game.cards import Card

        deck = build_deck()
        deal_rng.shuffle(deck)
        all_hands = [deck[i*11:(i+1)*11] for i in range(4)]
        kitty = deck[44:47]

        # Declarer picks up kitty and discards
        hand_14 = all_hands[DECLARER] + kitty
        kept, _ = best_kitty_discard(hand_14, TRUMP_SUIT, nullo=False)
        all_hands[DECLARER] = kept

        for name, play_fn in play_fns.items():
            sim_rng = random.Random(seed)  # same RNG state for rollout randomness
            tricks = simulate_game(all_hands, contract, TRUMP_SUIT, sim_rng, play_fn)
            results[name].append(tricks)

    # Print summary
    print(f"\n{'='*62}")
    print(f"Lead Strategy Benchmark — {N_DEALS} paired deals (8H contract)")
    print(f"{'='*62}")
    print(f"{'Strategy':<35} {'Avg':>6} {'Std':>5} {'Delta vs A':>10}")
    print(f"{'-'*62}")

    baseline_avg = statistics.mean(results["A (baseline)"])
    for name, tricks in results.items():
        avg = statistics.mean(tricks)
        std = statistics.stdev(tricks) if len(tricks) > 1 else 0.0
        delta = avg - baseline_avg
        marker = " ◀ best" if avg == max(statistics.mean(v) for v in results.values()) else ""
        print(f"{name:<35} {avg:>6.3f} {std:>5.2f} {delta:>+10.3f}{marker}")

    print(f"\nBaseline (A) avg: {baseline_avg:.3f} tricks")

    # Head-to-head pairwise wins
    print(f"\n{'─'*62}")
    print("Pairwise head-to-head wins (per deal):")
    names = list(results.keys())
    for i, n1 in enumerate(names):
        for n2 in names[i+1:]:
            wins1 = sum(1 for a, b in zip(results[n1], results[n2]) if a > b)
            wins2 = sum(1 for a, b in zip(results[n1], results[n2]) if b > a)
            ties = N_DEALS - wins1 - wins2
            print(f"  {n1} vs {n2}: {wins1}-{wins2} ({ties} ties)")


if __name__ == "__main__":
    print(f"Running Phase 3 benchmark ({N_DEALS} deals)…")
    run_benchmark()
