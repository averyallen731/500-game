"""
Phase 1 tests: card model, deck, trick resolution, legal plays, bidding.
Run with: pytest tests/test_phase1.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
import pytest
from backend.game.cards import Card, Suit, Rank, JOKER, card_rank_in_context
from backend.game.deck import build_deck, deal
from backend.game.tricks import (
    winning_card_index, cards_following_suit, is_legal_play, legal_plays, get_led_suit
)
from backend.game.bidding import Bid, BidSuit, NULLO, DOUBLE_NULLO, all_bids


# ── Helpers ──────────────────────────────────────────────────────────────────

def c(rank_str: str, suit_str: str) -> Card:
    """Convenience: c('J', 'S') → Jack of Spades."""
    rank_map = {"3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
                "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT,
                "9": Rank.NINE, "10": Rank.TEN, "J": Rank.JACK,
                "Q": Rank.QUEEN, "K": Rank.KING, "A": Rank.ACE}
    suit_map = {"S": Suit.SPADES, "C": Suit.CLUBS, "H": Suit.HEARTS, "D": Suit.DIAMONDS}
    return Card(suit=suit_map[suit_str], rank=rank_map[rank_str])


# ── Deck tests ────────────────────────────────────────────────────────────────

def test_deck_size():
    assert len(build_deck()) == 47

def test_deck_has_one_joker():
    assert sum(1 for card in build_deck() if card.is_joker()) == 1

def test_deck_red_suits_have_3():
    deck = build_deck()
    for suit in (Suit.HEARTS, Suit.DIAMONDS):
        assert Card(suit=suit, rank=Rank.THREE) in deck

def test_deck_black_suits_no_3():
    deck = build_deck()
    for suit in (Suit.SPADES, Suit.CLUBS):
        assert Card(suit=suit, rank=Rank.THREE) not in deck

def test_deck_no_duplicates():
    deck = build_deck()
    assert len(deck) == len(set(deck))

def test_deal_sizes():
    hands, kitty = deal()
    assert len(hands) == 4
    assert all(len(h) == 11 for h in hands)
    assert len(kitty) == 3

def test_deal_all_unique():
    hands, kitty = deal()
    all_cards = [c for h in hands for c in h] + kitty
    assert len(all_cards) == 47
    assert len(set(all_cards)) == 47

def test_deal_reproducible_with_seed():
    rng = random.Random(42)
    hands1, kitty1 = deal(rng)
    rng = random.Random(42)
    hands2, kitty2 = deal(rng)
    assert hands1 == hands2
    assert kitty1 == kitty2


# ── Bower / card identity tests ───────────────────────────────────────────────

def test_right_bower_spades():
    assert c("J", "S").is_right_bower(Suit.SPADES)

def test_left_bower_spades():
    # Left bower of spades = Jack of Clubs (same color = black)
    assert c("J", "C").is_left_bower(Suit.SPADES)

def test_left_bower_hearts():
    # Left bower of hearts = Jack of Diamonds (same color = red)
    assert c("J", "D").is_left_bower(Suit.HEARTS)

def test_right_bower_not_left_bower():
    assert not c("J", "S").is_left_bower(Suit.SPADES)

def test_left_bower_not_right_bower():
    assert not c("J", "C").is_right_bower(Suit.SPADES)

def test_no_bowers_in_nt():
    assert not c("J", "S").is_right_bower(Suit.NO_TRUMP)
    assert not c("J", "C").is_left_bower(Suit.NO_TRUMP)

def test_joker_not_bower():
    assert not JOKER.is_right_bower(Suit.SPADES)
    assert not JOKER.is_left_bower(Suit.SPADES)


# ── Effective suit tests ──────────────────────────────────────────────────────

def test_left_bower_effective_suit_is_trump():
    # J♣ with spades trump → effective suit is spades
    assert c("J", "C").effective_suit(Suit.SPADES) == Suit.SPADES

def test_regular_card_effective_suit():
    assert c("A", "H").effective_suit(Suit.SPADES) == Suit.HEARTS

def test_joker_effective_suit_is_trump():
    assert JOKER.effective_suit(Suit.HEARTS) == Suit.HEARTS

def test_joker_effective_suit_nt_is_none():
    assert JOKER.effective_suit(Suit.NO_TRUMP) is None


# ── card_rank_in_context tests ────────────────────────────────────────────────

def test_joker_beats_all_trump():
    trump = Suit.SPADES
    right = c("J", "S")
    left = c("J", "C")
    ace = c("A", "S")
    joker_rank = card_rank_in_context(JOKER, trump, Suit.SPADES)
    assert joker_rank > card_rank_in_context(right, trump, Suit.SPADES)
    assert joker_rank > card_rank_in_context(left, trump, Suit.SPADES)
    assert joker_rank > card_rank_in_context(ace, trump, Suit.SPADES)

def test_right_bower_beats_left_bower():
    trump = Suit.SPADES
    right_rank = card_rank_in_context(c("J", "S"), trump, Suit.SPADES)
    left_rank = card_rank_in_context(c("J", "C"), trump, Suit.SPADES)
    assert right_rank > left_rank

def test_left_bower_beats_ace_of_trump():
    trump = Suit.SPADES
    left_rank = card_rank_in_context(c("J", "C"), trump, Suit.SPADES)
    ace_rank = card_rank_in_context(c("A", "S"), trump, Suit.SPADES)
    assert left_rank > ace_rank

def test_trump_beats_led_suit():
    trump = Suit.SPADES
    low_trump = card_rank_in_context(c("4", "S"), trump, Suit.HEARTS)
    high_led = card_rank_in_context(c("A", "H"), trump, Suit.HEARTS)
    assert low_trump > high_led

def test_off_suit_cannot_win():
    assert card_rank_in_context(c("A", "D"), Suit.SPADES, Suit.HEARTS) == 0

def test_joker_wins_in_nt():
    assert card_rank_in_context(JOKER, Suit.NO_TRUMP, Suit.CLUBS) == 117

def test_nt_no_trump_hierarchy():
    # In NT, only led-suit matters; ace beats king
    ace = card_rank_in_context(c("A", "H"), Suit.NO_TRUMP, Suit.HEARTS)
    king = card_rank_in_context(c("K", "H"), Suit.NO_TRUMP, Suit.HEARTS)
    assert ace > king

def test_nt_off_suit_zero():
    assert card_rank_in_context(c("A", "S"), Suit.NO_TRUMP, Suit.HEARTS) == 0


# ── Trick resolution tests ────────────────────────────────────────────────────

def test_winning_card_index_highest_trump():
    trump = Suit.SPADES
    trick = [c("A", "H"), c("4", "S"), c("K", "H"), c("A", "S")]
    # 4S and AS are both trump; AS wins (index 3)
    assert winning_card_index(trick, trump, Suit.HEARTS) == 3

def test_winning_card_index_joker_wins():
    trump = Suit.SPADES
    trick = [c("J", "S"), JOKER, c("A", "S"), c("K", "S")]
    assert winning_card_index(trick, trump, Suit.SPADES) == 1

def test_winning_card_index_led_suit_no_trump():
    trump = Suit.SPADES
    trick = [c("A", "H"), c("K", "H"), c("Q", "H"), c("J", "H")]
    assert winning_card_index(trick, trump, Suit.HEARTS) == 0

def test_winning_card_index_nt():
    trick = [c("A", "C"), c("K", "C"), JOKER, c("5", "C")]
    assert winning_card_index(trick, Suit.NO_TRUMP, Suit.CLUBS) == 2  # joker


# ── Following-suit and legal play tests ──────────────────────────────────────

def test_must_follow_suit():
    hand = [c("5", "H"), c("A", "S"), c("K", "D")]
    # Hearts led, player has hearts → must play hearts
    following = cards_following_suit(hand, Suit.HEARTS, Suit.SPADES)
    assert following == [c("5", "H")]

def test_left_bower_must_follow_trump():
    # J♣ with spades trump: treated as spades, NOT clubs
    hand = [c("J", "C"), c("5", "C"), c("A", "H")]
    # Clubs led: J♣ is treated as spades, so only 5♣ follows clubs
    following = cards_following_suit(hand, Suit.CLUBS, Suit.SPADES)
    assert c("J", "C") not in following
    assert c("5", "C") in following

def test_left_bower_follows_trump_lead():
    hand = [c("J", "C"), c("5", "H"), c("A", "D")]
    # Spades (trump) led: J♣ is trump, must follow
    following = cards_following_suit(hand, Suit.SPADES, Suit.SPADES)
    assert c("J", "C") in following

def test_void_allows_any_card():
    hand = [c("A", "S"), c("K", "D")]
    # Hearts led, no hearts in hand → void, any card legal
    assert is_legal_play(c("A", "S"), hand, Suit.HEARTS, Suit.SPADES)
    assert is_legal_play(c("K", "D"), hand, Suit.HEARTS, Suit.SPADES)

def test_cannot_play_card_not_in_hand():
    hand = [c("A", "S")]
    assert not is_legal_play(c("K", "H"), hand, Suit.HEARTS, Suit.SPADES)

def test_leading_any_card_is_legal():
    hand = [c("5", "H"), c("A", "S")]
    assert is_legal_play(c("5", "H"), hand, None, Suit.SPADES)
    assert is_legal_play(c("A", "S"), hand, None, Suit.SPADES)

def test_legal_plays_returns_all_on_lead():
    hand = [c("5", "H"), c("A", "S"), c("K", "D")]
    assert set(legal_plays(hand, None, Suit.SPADES)) == set(hand)

def test_legal_plays_restricted_when_following():
    hand = [c("5", "H"), c("A", "H"), c("K", "S")]
    plays = legal_plays(hand, Suit.HEARTS, Suit.SPADES)
    assert set(plays) == {c("5", "H"), c("A", "H")}


# ── get_led_suit tests ────────────────────────────────────────────────────────

def test_get_led_suit_normal():
    assert get_led_suit(c("A", "H"), Suit.SPADES) == Suit.HEARTS

def test_get_led_suit_left_bower():
    # J♣ leads with spades trump → led suit = spades
    assert get_led_suit(c("J", "C"), Suit.SPADES) == Suit.SPADES

def test_get_led_suit_joker_trump_contract():
    assert get_led_suit(JOKER, Suit.HEARTS) == Suit.HEARTS

def test_get_led_suit_joker_nt_requires_declaration():
    assert get_led_suit(JOKER, Suit.NO_TRUMP, nt_declared_suit=Suit.CLUBS) == Suit.CLUBS

def test_get_led_suit_joker_nt_raises_without_declaration():
    with pytest.raises(ValueError):
        get_led_suit(JOKER, Suit.NO_TRUMP)


# ── Bidding tests ─────────────────────────────────────────────────────────────

def test_all_bids_count():
    # 6 trick levels × 5 suits + nullo + double nullo = 32
    assert len(all_bids()) == 32

def test_bids_sorted_by_value():
    bids = all_bids()
    values = [b.point_value for b in bids]
    assert values == sorted(values)

def test_nullo_between_8s_and_8c():
    # Nullo = 250 pts, 8S = 240, 8C = 260
    bids = all_bids()
    names = [repr(b) for b in bids]
    nullo_idx = names.index("Nullo")
    eight_s = names.index("8S")
    eight_c = names.index("8C")
    assert eight_s < nullo_idx < eight_c

def test_bid_trump_suit_mapping():
    assert Bid(tricks=7, suit=BidSuit.HEARTS).trump_suit == Suit.HEARTS
    assert Bid(tricks=7, suit=BidSuit.NO_TRUMP).trump_suit == Suit.NO_TRUMP
    assert NULLO.trump_suit is None

def test_double_nullo_value():
    assert DOUBLE_NULLO.point_value == 500
