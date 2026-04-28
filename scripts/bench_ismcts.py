"""
Quick ISMCTS vs heuristic head-to-head with the UPDATED heuristic.

Two teams: ISMCTS (seats 0+2) vs Heuristic (seats 1+3).
Then swap roles to cancel out positional bias.
Reports avg declaring-side tricks per deal.

Run from project root:
    python3 -m scripts.bench_ismcts
"""
from __future__ import annotations

import random
import statistics
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.game.cards import Suit
from backend.game.bidding import Contract, Bid, BidSuit
from backend.game.tricks import play_order, winning_seat, legal_plays
from backend.game.hand import best_kitty_discard
from backend.game.deck import build_deck
from backend.solver.heuristic import play_card as heuristic_play
from backend.solver.ismcts import run_ismcts

N_DEALS = 40
DECLARER = 0          # North is declarer for all deals
TRUMP_SUIT = Suit.HEARTS
TRUMP_CHOICE = BidSuit.HEARTS
ISMCTS_ITER = 300
ISMCTS_TIME = 0.3


def deal_hands(rng):
    deck = build_deck()
    rng.shuffle(deck)
    hands = [deck[i*11:(i+1)*11] for i in range(4)]
    kitty = deck[44:47]
    contract = Contract(bid=Bid(tricks=8, suit=TRUMP_CHOICE), declarer=DECLARER)
    hand_14 = hands[DECLARER] + kitty
    kept, _ = best_kitty_discard(hand_14, TRUMP_SUIT, nullo=False)
    hands[DECLARER] = kept
    return hands, contract


def simulate(hands_in, contract, trump, rng, ismcts_seats: set[int]) -> int:
    """Play 11 tricks; ISMCTS seats use run_ismcts, others use heuristic."""
    hands = [list(h) for h in hands_in]
    played_cards: set = set()
    leader = contract.declarer
    active = contract.active_seats
    dec_tricks = 0
    dec_tricks_done = 0
    tricks_done = 0

    for _ in range(11):
        trick_cards = []
        playing_order = play_order(leader, active)
        led_suit = None

        for seat in playing_order:
            if seat in ismcts_seats:
                card = run_ismcts(
                    root_seat=seat,
                    root_hand=list(hands[seat]),
                    played_cards=set(played_cards),
                    trick_so_far=list(trick_cards),
                    trick_seats_so_far=list(playing_order[:len(trick_cards)]),
                    contract=contract,
                    trump=trump,
                    leader=leader,
                    dec_tricks_so_far=dec_tricks,
                    tricks_done=tricks_done,
                    rng=rng,
                    iterations=ISMCTS_ITER,
                    time_budget_s=ISMCTS_TIME,
                )
            else:
                card = heuristic_play(
                    seat=seat, hand=hands[seat], trick_so_far=trick_cards,
                    leader_seat=leader, led_suit=led_suit, trump=trump,
                    contract=contract, played_cards=played_cards, rng=rng,
                )

            hands[seat].remove(card)
            trick_cards.append(card)
            played_cards.add(card)

            if led_suit is None:
                if card.is_joker() and trump == Suit.NO_TRUMP:
                    suit_counts = {}
                    for c in hands[seat]:
                        if not c.is_joker() and c.suit:
                            suit_counts[c.suit] = suit_counts.get(c.suit, 0) + 1
                    led_suit = max(suit_counts, key=suit_counts.get) if suit_counts else Suit.SPADES
                else:
                    eff = card.effective_suit(trump)
                    led_suit = eff or Suit.SPADES

        winner = winning_seat(trick_cards, trump, led_suit, playing_order)
        if contract.is_declarer_side(winner):
            dec_tricks += 1
        tricks_done += 1
        leader = winner

    return dec_tricks


def run_benchmark():
    rng_master = random.Random(99)
    seeds = [rng_master.randint(0, 2**32) for _ in range(N_DEALS)]

    # Condition A: ISMCTS plays for declaring side (seats 0+2)
    ismcts_declaring = []
    # Condition B: ISMCTS plays for opposition (seats 1+3) — tests defence quality
    ismcts_defending = []
    # Condition C: pure heuristic both sides (baseline)
    pure_heuristic = []

    for i, seed in enumerate(seeds):
        if (i + 1) % 10 == 0:
            print(f"  Deal {i+1}/{N_DEALS}…")

        deal_rng = random.Random(seed)
        hands, contract = deal_hands(deal_rng)

        # Pure heuristic baseline (no ISMCTS)
        sim_rng = random.Random(seed)
        t_h = simulate(hands, contract, TRUMP_SUIT, sim_rng, ismcts_seats=set())
        pure_heuristic.append(t_h)

        # ISMCTS on declaring side
        sim_rng = random.Random(seed)
        t_d = simulate(hands, contract, TRUMP_SUIT, sim_rng, ismcts_seats={0, 2})
        ismcts_declaring.append(t_d)

        # ISMCTS on defending side
        sim_rng = random.Random(seed)
        t_def = simulate(hands, contract, TRUMP_SUIT, sim_rng, ismcts_seats={1, 3})
        ismcts_defending.append(t_def)

    avg_h   = statistics.mean(pure_heuristic)
    avg_d   = statistics.mean(ismcts_declaring)
    avg_def = statistics.mean(ismcts_defending)

    print(f"\n{'='*56}")
    print(f"ISMCTS vs Heuristic head-to-head ({N_DEALS} deals, 8H)")
    print(f"{'='*56}")
    print(f"Pure heuristic (both sides)   : {avg_h:.3f} declarer tricks")
    print(f"ISMCTS declaring (vs heuristic): {avg_d:.3f}  Δ={avg_d-avg_h:+.3f}")
    print(f"ISMCTS defending (vs heuristic): {avg_def:.3f}  Δ={avg_def-avg_h:+.3f}")
    print()
    print("Interpretation:")
    print(f"  ISMCTS declaring advantage : {avg_d-avg_h:+.3f} tricks/deal")
    print(f"  ISMCTS defending advantage : {avg_h-avg_def:+.3f} tricks/deal")


if __name__ == "__main__":
    print(f"Running ISMCTS head-to-head ({N_DEALS} deals, {ISMCTS_ITER} iters/card)…")
    run_benchmark()
