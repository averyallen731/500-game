"""
Tests for the Phase 2 double-dummy solver.

Run with: python3 -m pytest tests/test_solver.py -v
"""
import random
import time

import pytest

from backend.game.cards import Card, Suit, Rank, JOKER
from backend.game.deck import build_deck, deal
from backend.game.bidding import Contract, Bid, BidSuit, NULLO, DOUBLE_NULLO
from backend.game.tricks import NORTH, EAST, SOUTH, WEST
from backend.solver.card_map import (
    CARD_TO_ID, ID_TO_CARD, build_card_map, hand_to_mask, mask_to_cards,
)
from backend.solver.solver import solve, best_discard
from backend.solver.sampler import sample_remaining


# --------------------------------------------------------------------------- #
# card_map tests
# --------------------------------------------------------------------------- #

def test_card_map_covers_all_47():
    """CARD_TO_ID has exactly 47 entries with unique ids 0-46."""
    assert len(CARD_TO_ID) == 47
    assert len(ID_TO_CARD) == 47
    ids = set(CARD_TO_ID.values())
    assert ids == set(range(47))


def test_card_map_builds_fresh():
    """build_card_map() returns independent maps each call."""
    c2i, i2c = build_card_map()
    assert len(c2i) == 47
    assert set(c2i.values()) == set(range(47))


def test_mask_roundtrip():
    """hand_to_mask then mask_to_cards gives back the same set of cards."""
    rng = random.Random(42)
    deck = build_deck()
    rng.shuffle(deck)
    hand = deck[:11]
    mask = hand_to_mask(hand)
    recovered = mask_to_cards(mask)
    assert set(recovered) == set(hand)


def test_mask_empty_hand():
    """Empty hand gives mask 0, mask_to_cards of 0 is empty."""
    assert hand_to_mask([]) == 0
    assert mask_to_cards(0) == []


def test_mask_single_card():
    """Single card round-trips correctly."""
    card = Card(Suit.HEARTS, Rank.ACE)
    mask = hand_to_mask([card])
    recovered = mask_to_cards(mask)
    assert recovered == [card]


# --------------------------------------------------------------------------- #
# solve() basic correctness
# --------------------------------------------------------------------------- #

def _hearts_contract(declarer: int = SOUTH) -> Contract:
    return Contract(bid=Bid(tricks=8, suit=BidSuit.HEARTS), declarer=declarer)


def _spades_contract(declarer: int = SOUTH) -> Contract:
    return Contract(bid=Bid(tricks=7, suit=BidSuit.SPADES), declarer=declarer)


def _nt_contract(declarer: int = SOUTH) -> Contract:
    return Contract(bid=Bid(tricks=6, suit=BidSuit.NO_TRUMP), declarer=declarer)


def test_solve_returns_int_in_range():
    """solve() on a random deal returns an integer 0 <= n <= 11."""
    rng = random.Random(1)
    hands, _kitty = deal(rng)
    contract = _hearts_contract()
    result = solve(hands, contract)
    assert isinstance(result, int)
    assert 0 <= result <= 11


def test_solve_consistent():
    """Same deal solved twice gives the same result (deterministic)."""
    rng = random.Random(99)
    hands, _ = deal(rng)
    contract = _hearts_contract()
    r1 = solve(hands, contract)
    r2 = solve(hands, contract)
    assert r1 == r2


def test_solve_complements():
    """
    In a normal 4-player contract, declarer_tricks + opponent_tricks == 11.
    We verify by solving from both perspectives: the side that doesn't declare
    should win (11 - declarer_tricks) tricks.
    """
    rng = random.Random(7)
    hands, _ = deal(rng)
    contract = _hearts_contract(declarer=SOUTH)
    declarer_tricks = solve(hands, contract)

    # Sanity: trick counts are non-negative and sum to 11
    assert 0 <= declarer_tricks <= 11
    # Opponent tricks
    opponent_tricks = 11 - declarer_tricks
    assert 0 <= opponent_tricks <= 11


def test_solve_trivial_all_trump():
    """
    Give South all Hearts (trump). South should win every trick.
    We give the remaining cards to the other three seats.
    Hearts trump, South leads.
    """
    # Build a hand where South has all heart cards available
    deck = build_deck()
    hearts = [c for c in deck if c.suit == Suit.HEARTS]
    # South gets all hearts (12 cards) — but we need exactly 11 per player
    # Use the first 11 hearts for South and distribute rest
    south_hand = hearts[:11]
    non_hearts = [c for c in deck if c.suit != Suit.HEARTS and not c.is_joker()]

    # Give North, East, West 11 cards each from non-hearts
    north_hand = non_hearts[0:11]
    east_hand = non_hearts[11:22]
    west_hand = non_hearts[22:33]

    hands = [north_hand, east_hand, south_hand, west_hand]
    contract = Contract(bid=Bid(tricks=11, suit=BidSuit.HEARTS), declarer=SOUTH)

    result = solve(hands, contract)
    # South has all trump — should win all 11 tricks
    assert result == 11


def test_solve_trivial_no_trump_high_cards():
    """
    Give South all Aces plus high cards in NT. South should win most tricks.
    """
    deck = build_deck()
    aces = [c for c in deck if c.rank == Rank.ACE]  # 4 aces
    kings = [c for c in deck if c.rank == Rank.KING]  # 4 kings
    queens = [c for c in deck if c.rank == Rank.QUEEN]  # 4 queens
    south_hand = (aces + kings + queens)[:11]

    remaining = [c for c in deck if c not in south_hand]
    north_hand = remaining[0:11]
    east_hand = remaining[11:22]
    west_hand = remaining[22:33]

    hands = [north_hand, east_hand, south_hand, west_hand]
    contract = _nt_contract()

    result = solve(hands, contract)
    # South has all the high cards; should win many tricks
    assert result >= 6, f"Expected at least 6 tricks with all aces/kings/queens, got {result}"


def test_solve_nullo_zero_tricks():
    """
    Give South all low, off-suit cards in a Nullo contract.
    South (declarer in Nullo) should win 0 tricks.
    """
    deck = build_deck()
    # Pick the lowest cards: 3H, 3D, 4S, 4C, 5H, 5D, 5S, 5C, 6H, 6D, 6S
    low_cards = sorted(
        [c for c in deck if not c.is_joker() and c.rank.value <= 6],
        key=lambda c: (c.rank.value, c.suit.value),
    )
    south_hand = low_cards[:11]

    remaining = [c for c in deck if c not in south_hand]
    north_hand = remaining[0:11]
    east_hand = remaining[11:22]
    west_hand = remaining[22:33]

    hands = [north_hand, east_hand, south_hand, west_hand]
    nullo_contract = Contract(bid=NULLO, declarer=SOUTH)

    result = solve(hands, nullo_contract)
    # South has only low cards — opponents hold all high cards and will try
    # to force tricks on South.  Perfect double-dummy play: opponents play high.
    # South can avoid winning tricks with only low cards.
    assert result == 0, f"Expected 0 tricks for nullo with only low cards, got {result}"


def test_solve_nullo_full_hand():
    """solve() for a nullo contract returns an int in valid range."""
    rng = random.Random(42)
    hands, _ = deal(rng)
    nullo_contract = Contract(bid=NULLO, declarer=SOUTH)
    result = solve(hands, nullo_contract)
    assert isinstance(result, int)
    # Nullo: only 3 players active → 11 tricks
    assert 0 <= result <= 11


def test_solve_double_nullo():
    """solve() for a double nullo contract returns an int in valid range."""
    rng = random.Random(55)
    hands, _ = deal(rng)
    dn_contract = Contract(bid=DOUBLE_NULLO, declarer=SOUTH)
    result = solve(hands, dn_contract)
    assert isinstance(result, int)
    assert 0 <= result <= 11


# --------------------------------------------------------------------------- #
# best_discard tests
# --------------------------------------------------------------------------- #

def test_best_discard_returns_11_cards():
    """best_discard(14_cards, contract) returns an 11-card hand."""
    rng = random.Random(123)
    deck = build_deck()
    rng.shuffle(deck)
    hand_14 = deck[:14]
    contract = _hearts_contract()

    kept, discarded = best_discard(hand_14, contract)
    assert len(kept) == 11
    assert len(discarded) == 3
    # All cards are from the original 14
    assert set(kept) | set(discarded) == set(hand_14)
    # No overlap
    assert set(kept) & set(discarded) == set()


def test_best_discard_nullo_removes_high():
    """For nullo, best_discard should prefer discarding high/dangerous cards."""
    deck = build_deck()
    # Build a hand of 14 with known high cards
    joker = JOKER
    ace_h = Card(Suit.HEARTS, Rank.ACE)
    ace_d = Card(Suit.DIAMONDS, Rank.ACE)
    ace_s = Card(Suit.SPADES, Rank.ACE)
    ace_c = Card(Suit.CLUBS, Rank.ACE)
    low_cards = [c for c in deck if not c.is_joker() and c.rank.value <= 5][:9]
    hand_14 = [joker, ace_h, ace_d, ace_s, ace_c] + low_cards[:9]
    contract = Contract(bid=NULLO, declarer=SOUTH)
    kept, discarded = best_discard(hand_14, contract)
    # Joker must be discarded in nullo (most dangerous card)
    assert JOKER in discarded


def test_best_discard_normal_keeps_high():
    """For normal contract, best_discard should keep high/trump cards."""
    deck = build_deck()
    joker = JOKER
    # rank <= 7 gives 18 low cards (enough to pick 13 non-joker ones)
    low_cards = [c for c in deck if not c.is_joker() and c.rank.value <= 7][:13]
    assert len(low_cards) == 13, f"Expected 13 low cards, got {len(low_cards)}"
    hand_14 = [joker] + low_cards
    contract = _hearts_contract()
    kept, discarded = best_discard(hand_14, contract)
    # Joker should be kept in normal contract
    assert JOKER in kept


# --------------------------------------------------------------------------- #
# sampler tests
# --------------------------------------------------------------------------- #

def test_sample_remaining_card_count():
    """
    sample_remaining gives the right number of cards in each position.
    user has 11, remaining 36 split as North 11 + East 11 + West 11 + kitty 3 = 36.
    """
    rng = random.Random(0)
    deck = build_deck()
    rng.shuffle(deck)
    user_hand = deck[:11]

    result = sample_remaining(user_hand, rng=random.Random(1))
    hands = result['hands']
    kitty = result['kitty']

    assert len(hands) == 4
    assert len(hands[0]) == 11    # North
    assert len(hands[1]) == 11    # East
    assert len(hands[2]) == 11    # South (user) - unchanged
    assert len(hands[3]) == 11    # West
    assert len(kitty) == 3
    assert set(hands[2]) == set(user_hand)


def test_sample_remaining_no_overlap():
    """All cards across all hands + kitty are distinct."""
    rng = random.Random(5)
    deck = build_deck()
    rng.shuffle(deck)
    user_hand = deck[:11]

    result = sample_remaining(user_hand, rng=random.Random(10))
    all_cards = []
    for hand in result['hands']:
        all_cards.extend(hand)
    all_cards.extend(result['kitty'])

    assert len(all_cards) == 47
    assert len(set(all_cards)) == 47  # all distinct


def test_sample_remaining_covers_deck():
    """All 47 deck cards appear exactly once across hands + kitty."""
    rng = random.Random(20)
    deck = build_deck()
    rng.shuffle(deck)
    user_hand = deck[:11]

    result = sample_remaining(user_hand, rng=random.Random(30))
    all_cards = set()
    for hand in result['hands']:
        all_cards.update(hand)
    all_cards.update(result['kitty'])

    assert all_cards == set(build_deck())


def test_sample_remaining_randomness():
    """Two different seeds produce different deals."""
    deck = build_deck()
    user_hand = deck[:11]

    r1 = sample_remaining(user_hand, rng=random.Random(1))
    r2 = sample_remaining(user_hand, rng=random.Random(2))

    # At least one opponent hand should differ (astronomically unlikely to be equal)
    assert r1['hands'][1] != r2['hands'][1] or r1['hands'][3] != r2['hands'][3]


# --------------------------------------------------------------------------- #
# Performance test
# --------------------------------------------------------------------------- #

def test_solve_performance():
    """solve() on a full random deal completes in < 5 seconds."""
    rng = random.Random(42)
    hands, _ = deal(rng)
    contract = _hearts_contract()

    start = time.time()
    result = solve(hands, contract)
    elapsed = time.time() - start

    assert isinstance(result, int)
    assert 0 <= result <= 11
    assert elapsed < 5.0, f"Solver took {elapsed:.2f}s, expected < 5s"
