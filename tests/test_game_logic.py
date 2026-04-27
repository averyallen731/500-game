"""
Extended game-logic tests covering:
  - Bidding process (ordering, point values, trump mapping)
  - Kitty pickup and discard (normal + nullo)
  - Trick winner leads next trick
  - Following suit in multi-trick sequences
  - Edge cases: void suits, left bower, joker in NT/trump contracts
  - Seat tracking across a full 11-trick game

Run with: pytest tests/test_game_logic.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
import pytest
from backend.game.cards import Card, Suit, Rank, JOKER, card_rank_in_context
from backend.game.deck import build_deck, deal
from backend.game.tricks import (
    winning_card_index, winning_seat, play_order, cards_following_suit,
    is_legal_play, legal_plays, get_led_suit,
    NORTH, EAST, SOUTH, WEST, is_declarer_team,
)
from backend.game.bidding import Bid, BidSuit, NULLO, DOUBLE_NULLO, all_bids, Contract
from backend.game.hand import analyze_hand, best_kitty_discard, HandAnalysis


# ── Helpers ───────────────────────────────────────────────────────────────────

def c(rank_str: str, suit_str: str) -> Card:
    rank_map = {"3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
                "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT,
                "9": Rank.NINE, "10": Rank.TEN, "J": Rank.JACK,
                "Q": Rank.QUEEN, "K": Rank.KING, "A": Rank.ACE}
    suit_map = {"S": Suit.SPADES, "C": Suit.CLUBS, "H": Suit.HEARTS, "D": Suit.DIAMONDS}
    return Card(suit=suit_map[suit_str], rank=rank_map[rank_str])


# ═══════════════════════════════════════════════════════════════════════════════
# BIDDING PROCESS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBiddingProcess:

    def test_bid_count(self):
        assert len(all_bids()) == 32   # 6 levels × 5 suits + nullo + double nullo

    def test_non_decreasing_values(self):
        # Point values are non-decreasing. The one known tie is 10H == Double Nullo == 500.
        bids = all_bids()
        for i in range(len(bids) - 1):
            assert bids[i].point_value <= bids[i + 1].point_value, (
                f"Bid order broken: {bids[i]} ({bids[i].point_value}) > "
                f"{bids[i+1]} ({bids[i+1].point_value})"
            )

    def test_double_nullo_ordered_after_10h(self):
        # 10H and Double Nullo both worth 500 pts; Double Nullo outranks 10H
        bids = all_bids()
        names = [repr(b) for b in bids]
        assert names.index("10H") < names.index("Double Nullo")

    def test_suit_order_within_level(self):
        # Within each trick level: S < C < D < H < NT
        bids = all_bids()
        for tricks in range(6, 12):
            level = [b for b in bids if b.tricks == tricks]
            suits = [b.suit for b in level]
            assert suits == [BidSuit.SPADES, BidSuit.CLUBS, BidSuit.DIAMONDS,
                             BidSuit.HEARTS, BidSuit.NO_TRUMP], \
                f"Wrong suit order at {tricks}-trick level: {suits}"

    def test_nullo_slots_between_8s_and_8c(self):
        bids = all_bids()
        names = [repr(b) for b in bids]
        assert names.index("8S") < names.index("Nullo") < names.index("8C")

    def test_11nt_is_highest_bid(self):
        # 11NT = 620 pts, the highest bid in 500.
        # Double Nullo (500 pts) is NOT the highest — it ties 10H.
        bids = all_bids()
        assert bids[-1] == Bid(11, BidSuit.NO_TRUMP)

    def test_double_nullo_between_10h_and_10nt(self):
        bids = all_bids()
        names = [repr(b) for b in bids]
        assert names.index("10H") < names.index("Double Nullo") < names.index("10NT")

    def test_known_point_values(self):
        assert Bid(6, BidSuit.SPADES).point_value == 40
        assert Bid(6, BidSuit.NO_TRUMP).point_value == 120
        assert Bid(10, BidSuit.HEARTS).point_value == 500
        assert NULLO.point_value == 250
        assert DOUBLE_NULLO.point_value == 500

    def test_trump_suit_extraction(self):
        assert Bid(7, BidSuit.SPADES).trump_suit == Suit.SPADES
        assert Bid(7, BidSuit.CLUBS).trump_suit == Suit.CLUBS
        assert Bid(7, BidSuit.HEARTS).trump_suit == Suit.HEARTS
        assert Bid(7, BidSuit.DIAMONDS).trump_suit == Suit.DIAMONDS
        assert Bid(7, BidSuit.NO_TRUMP).trump_suit == Suit.NO_TRUMP
        assert NULLO.trump_suit is None
        assert DOUBLE_NULLO.trump_suit is None

    def test_nullo_is_nullo(self):
        assert NULLO.is_nullo
        assert DOUBLE_NULLO.is_nullo
        assert not Bid(7, BidSuit.HEARTS).is_nullo

    def test_double_nullo_flag(self):
        assert DOUBLE_NULLO.is_double_nullo
        assert not NULLO.is_double_nullo

    def test_bid_repr(self):
        assert repr(Bid(8, BidSuit.HEARTS)) == "8H"
        assert repr(Bid(6, BidSuit.NO_TRUMP)) == "6NT"
        assert repr(NULLO) == "Nullo"
        assert repr(DOUBLE_NULLO) == "Double Nullo"


# ═══════════════════════════════════════════════════════════════════════════════
# KITTY PICKUP AND DISCARD
# ═══════════════════════════════════════════════════════════════════════════════

class TestKittyDiscard:

    def _make_hand_14(self, trump: Suit) -> list[Card]:
        """Builds a 14-card hand: several trump + kitty of junk."""
        hand = [
            c("A", "S"), c("K", "S"), c("J", "S"),  # 3 spades
            c("J", "C"),                              # left bower (if S trump)
            c("5", "H"), c("6", "H"),                # 2 hearts
            c("4", "D"), c("5", "D"),                # 2 diamonds
            c("6", "C"), c("7", "C"), c("8", "C"),   # 3 clubs
            JOKER,
            # kitty:
            c("3", "H"), c("3", "D"),
        ]
        return hand

    def test_returns_11_kept_3_discarded(self):
        hand_14 = self._make_hand_14(Suit.SPADES)
        kept, discarded = best_kitty_discard(hand_14, Suit.SPADES)
        assert len(kept) == 11
        assert len(discarded) == 3

    def test_all_cards_accounted_for(self):
        hand_14 = self._make_hand_14(Suit.SPADES)
        kept, discarded = best_kitty_discard(hand_14, Suit.SPADES)
        assert set(kept) | set(discarded) == set(hand_14)
        assert len(set(kept) & set(discarded)) == 0

    def test_joker_never_discarded_in_normal_contract(self):
        hand_14 = self._make_hand_14(Suit.SPADES)
        kept, discarded = best_kitty_discard(hand_14, Suit.SPADES)
        assert JOKER not in discarded

    def test_right_bower_never_discarded(self):
        hand_14 = self._make_hand_14(Suit.SPADES)
        kept, discarded = best_kitty_discard(hand_14, Suit.SPADES)
        assert c("J", "S") not in discarded   # right bower of spades

    def test_left_bower_never_discarded(self):
        hand_14 = self._make_hand_14(Suit.SPADES)
        kept, discarded = best_kitty_discard(hand_14, Suit.SPADES)
        assert c("J", "C") not in discarded   # left bower of spades

    def test_low_off_suit_cards_discarded(self):
        # The 3♥ and 3♦ are the lowest non-trump; expect them discarded
        hand_14 = self._make_hand_14(Suit.SPADES)
        kept, discarded = best_kitty_discard(hand_14, Suit.SPADES)
        assert c("3", "H") in discarded
        assert c("3", "D") in discarded

    def test_requires_14_cards(self):
        with pytest.raises(ValueError):
            best_kitty_discard([c("A", "S")] * 13, Suit.SPADES)

    def test_nullo_discard_joker_first(self):
        hand_14 = [
            JOKER,
            c("A", "S"), c("K", "S"), c("Q", "S"),
            c("A", "H"), c("K", "H"), c("Q", "H"),
            c("A", "C"), c("K", "C"),
            c("4", "D"), c("5", "D"), c("6", "D"),
            c("3", "H"), c("3", "D"),
        ]
        kept, discarded = best_kitty_discard(hand_14, Suit.SPADES, nullo=True)
        # Joker is most dangerous in nullo — must be discarded
        assert JOKER in discarded

    def test_nullo_discard_high_cards(self):
        # Hand with clear best-discard candidates: aces and high trump
        hand_14 = [
            c("A", "S"), c("K", "S"),   # high trump (dangerous)
            c("J", "S"),                # right bower (most dangerous)
            c("A", "H"), c("A", "C"),   # high non-trump
            c("3", "H"), c("4", "H"), c("5", "H"),
            c("3", "D"), c("4", "D"), c("5", "D"),
            c("4", "C"), c("5", "C"), c("6", "C"),
        ]
        kept, discarded = best_kitty_discard(hand_14, Suit.SPADES, nullo=True)
        # Right bower is the most dangerous — must be discarded
        assert c("J", "S") in discarded

    def test_discard_with_full_deal(self):
        """Simulate a realistic kitty pickup from an actual deal."""
        rng = random.Random(0)
        hands, kitty = deal(rng)
        south_hand = hands[SOUTH]
        hand_14 = south_hand + kitty
        kept, discarded = best_kitty_discard(hand_14, Suit.HEARTS)
        assert len(kept) == 11
        assert len(discarded) == 3
        assert set(kept) | set(discarded) == set(hand_14)


# ═══════════════════════════════════════════════════════════════════════════════
# HAND ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHandAnalysis:

    def test_trump_count_includes_joker_and_bowers(self):
        hand = [JOKER, c("J", "S"), c("J", "C"), c("A", "S"), c("K", "S")]
        # S trump: joker + J♠ (right) + J♣ (left) + A♠ + K♠ = 5 trump
        a = analyze_hand(hand, Suit.SPADES)
        assert a.trump_count == 5

    def test_left_bower_counts_as_trump_not_natural_suit(self):
        hand = [c("J", "C"), c("5", "C"), c("9", "C")]
        # S trump: J♣ = left bower → trump length = 1, club length = 2
        a = analyze_hand(hand, Suit.SPADES)
        assert a.suit_lengths.get(Suit.SPADES, 0) == 1  # left bower
        assert a.suit_lengths.get(Suit.CLUBS, 0) == 2   # 5♣, 9♣

    def test_void_suits_detected(self):
        hand = [c("A", "S"), c("K", "S"), c("A", "H"), c("K", "H"),
                c("A", "C"), c("K", "C"), c("A", "D")]
        # No void suits
        a = analyze_hand(hand, Suit.SPADES)
        assert Suit.HEARTS not in a.void_suits
        assert Suit.CLUBS not in a.void_suits
        assert Suit.DIAMONDS not in a.void_suits

    def test_void_suit_missing(self):
        hand = [c("A", "S"), c("K", "S"), c("A", "H"), c("K", "H"),
                c("A", "C"), c("K", "C"), c("5", "S")]
        # No diamonds → void
        a = analyze_hand(hand, Suit.SPADES)
        assert Suit.DIAMONDS in a.void_suits

    def test_hcp_calculation(self):
        # J♣ with Spades trump IS the left bower → counts as trump, NOT as HCP.
        # Use J♥ instead (not a bower under Spades trump) so it contributes 1 HCP.
        hand = [c("A", "H"), c("K", "H"), c("Q", "D"), c("J", "H")]
        # A=4, K=3, Q=2, J♥=1 → 10
        a = analyze_hand(hand, Suit.SPADES)
        assert a.high_card_points == 10

    def test_bower_not_counted_as_hcp(self):
        # J♣ is left bower of Spades — should NOT add to HCP, only to trump count
        hand = [c("J", "C"), c("5", "H")]
        a = analyze_hand(hand, Suit.SPADES)
        assert a.has_left_bower
        assert a.high_card_points == 0  # left bower gives no HCP

    def test_joker_nt_not_counted_in_any_suit(self):
        hand = [JOKER, c("A", "H")]
        a = analyze_hand(hand, Suit.NO_TRUMP)
        assert a.has_joker
        # Joker shouldn't inflate any suit length in NT
        for suit in [Suit.SPADES, Suit.CLUBS, Suit.HEARTS, Suit.DIAMONDS]:
            if suit != Suit.HEARTS:
                assert a.suit_lengths.get(suit, 0) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# WINNER LEADS NEXT TRICK
# ═══════════════════════════════════════════════════════════════════════════════

class TestWinnerLeadsNext:

    def test_winning_seat_basic(self):
        # South (2) leads hearts trump, East (1) plays highest
        trump = Suit.HEARTS
        leader = SOUTH   # 2
        trick = [c("5", "H"), c("9", "H"), c("A", "H"), c("7", "H")]
        # play order: South, West, North, East
        # A♥ is at index 2 → North (0)
        led = Suit.HEARTS
        assert winning_seat(trick, trump, led, leader) == NORTH

    def test_winning_seat_east_wins(self):
        trump = Suit.SPADES
        leader = NORTH   # 0
        # play order: North, East, South, West
        trick = [c("5", "H"), c("A", "H"), c("K", "H"), c("Q", "H")]
        # A♥ at index 1 → East (1)
        assert winning_seat(trick, trump, Suit.HEARTS, leader) == EAST

    def test_winning_seat_trumping_in(self):
        trump = Suit.SPADES
        leader = SOUTH   # 2, play order: S, W, N, E
        trick = [c("A", "H"), c("4", "S"), c("K", "H"), c("Q", "H")]
        # 4♠ (trump) at index 1 → West (3)
        assert winning_seat(trick, trump, Suit.HEARTS, leader) == WEST

    def test_winner_leads_next_trick_chain(self):
        """Simulate 3 tricks and verify the leader updates correctly."""
        trump = Suit.SPADES
        results = []

        # Trick 1: South leads, North wins (A♥ at index 2)
        t1 = [c("5", "H"), c("6", "H"), c("A", "H"), c("K", "H")]
        # play order: S(2), W(3), N(0), E(1)
        seat1 = winning_seat(t1, trump, Suit.HEARTS, SOUTH)
        assert seat1 == NORTH
        results.append(seat1)

        # Trick 2: North leads, East wins (A♠ trump at index 3)
        # play order: N(0), E(1), S(2), W(3)
        t2 = [c("5", "C"), c("6", "C"), c("K", "C"), c("A", "S")]
        # A♠ is trump, beats all clubs; it's at index 3 → West (3)
        seat2 = winning_seat(t2, trump, Suit.CLUBS, seat1)
        assert seat2 == WEST

        # Trick 3: West leads; South plays joker and wins
        # play order: W(3), N(0), E(1), S(2)
        t3 = [c("A", "D"), c("K", "D"), c("Q", "D"), JOKER]
        seat3 = winning_seat(t3, trump, Suit.DIAMONDS, seat2)
        assert seat3 == SOUTH

        assert results == [NORTH]  # sanity check

    def test_declarer_team_membership(self):
        assert is_declarer_team(SOUTH)
        assert is_declarer_team(NORTH)
        assert not is_declarer_team(EAST)
        assert not is_declarer_team(WEST)

    def test_joker_wins_from_any_seat(self):
        trump = Suit.HEARTS
        for leader in range(4):
            for joker_pos in range(4):
                trick = [c("A", "H"), c("K", "H"), c("Q", "H"), c("J", "H")]
                trick[joker_pos] = JOKER
                assert winning_seat(trick, trump, Suit.HEARTS, leader) == (leader + joker_pos) % 4


# ═══════════════════════════════════════════════════════════════════════════════
# FOLLOWING SUIT — COMPLEX SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFollowingSuitComplex:

    def test_must_play_only_card_of_led_suit(self):
        # Left bower of HEARTS is J♦ (red suits pair), NOT J♣.
        # Left bower of SPADES is J♣ (black suits pair).
        # Use Spades trump so J♣ IS a bower and is void in clubs.
        hand = [c("J", "C"), c("A", "S"), c("K", "D"), c("5", "S")]
        # Spades trump, clubs led. J♣ = left bower (treated as spades, not clubs).
        # No regular clubs in hand → void → anything legal.
        plays = legal_plays(hand, Suit.CLUBS, Suit.SPADES)
        assert set(plays) == set(hand)

    def test_must_follow_regular_club_when_not_bower(self):
        # Confirm J♣ is a regular club when Hearts is trump (left bower of Hearts = J♦)
        hand = [c("J", "C"), c("A", "S"), c("K", "D"), c("5", "H")]
        # Hearts trump, clubs led. J♣ is NOT a bower here → must follow clubs.
        plays = legal_plays(hand, Suit.CLUBS, Suit.HEARTS)
        assert plays == [c("J", "C")]

    def test_left_bower_not_legal_when_following_its_natural_suit(self):
        # Spades trump, clubs led. J♣ is left bower = spades.
        # Player has J♣ and 8♣ → must play 8♣ (J♣ is trump, not clubs).
        hand = [c("J", "C"), c("8", "C"), c("A", "H")]
        plays = legal_plays(hand, Suit.CLUBS, Suit.SPADES)
        assert c("8", "C") in plays
        assert c("J", "C") not in plays

    def test_left_bower_must_be_played_when_trump_led(self):
        # Spades trump, spades led. J♣ is left bower = must follow.
        hand = [c("J", "C"), c("8", "H"), c("A", "D")]
        plays = legal_plays(hand, Suit.SPADES, Suit.SPADES)
        assert plays == [c("J", "C")]

    def test_joker_cannot_be_played_when_can_follow_trump_contract(self):
        # Hearts trump, hearts led. Player has joker + 5♥ → must follow trump.
        hand = [JOKER, c("5", "H"), c("A", "C")]
        plays = legal_plays(hand, Suit.HEARTS, Suit.HEARTS)
        # Both joker (trump) and 5♥ (trump) follow hearts
        assert JOKER in plays
        assert c("5", "H") in plays
        assert c("A", "C") not in plays

    def test_joker_cannot_be_played_when_can_follow_in_nt(self):
        # NT, clubs led. Player has joker + 5♣ → must follow clubs.
        # Joker has no suit in NT, so it doesn't "follow" clubs.
        hand = [JOKER, c("5", "C"), c("A", "H")]
        plays = legal_plays(hand, Suit.CLUBS, Suit.NO_TRUMP)
        assert c("5", "C") in plays
        assert JOKER not in plays  # must follow suit; joker ≠ clubs in NT

    def test_joker_legal_when_void_in_nt(self):
        # NT, clubs led. Player has joker + off-suit cards → void in clubs.
        hand = [JOKER, c("A", "H"), c("K", "D")]
        plays = legal_plays(hand, Suit.CLUBS, Suit.NO_TRUMP)
        assert JOKER in plays

    def test_void_in_trump_can_play_anything(self):
        trump = Suit.SPADES
        hand = [c("A", "H"), c("K", "D"), c("Q", "C")]
        # Spades led, no spades in hand (no trump)
        plays = legal_plays(hand, Suit.SPADES, trump)
        assert set(plays) == set(hand)

    def test_must_play_trump_when_trump_led_and_have_it(self):
        trump = Suit.DIAMONDS
        hand = [c("A", "H"), c("K", "C"), c("5", "D"), c("7", "D")]
        # Diamonds led; must follow trump
        plays = legal_plays(hand, Suit.DIAMONDS, trump)
        assert set(plays) == {c("5", "D"), c("7", "D")}
        assert c("A", "H") not in plays

    def test_over_ruffing_not_required(self):
        # Hearts trump, spades led, player is void in spades but has trump
        # Player does NOT have to play a higher trump than already played
        # (in 500 you must follow suit or play anything when void — you can
        #  play a low trump even if a higher trump is already in the trick)
        trump = Suit.HEARTS
        hand = [c("4", "H"), c("A", "H"), c("K", "C")]
        plays = legal_plays(hand, Suit.SPADES, trump)
        # Void in spades → can play anything (including low trump or off-suit)
        assert c("4", "H") in plays
        assert c("A", "H") in plays
        assert c("K", "C") in plays

    def test_full_four_card_trick_resolution(self):
        trump = Suit.CLUBS
        # South leads Q♥, West plays A♥, North plays 3♣ (trump!), East plays K♥
        trick = [c("Q", "H"), c("A", "H"), c("3", "C"), c("K", "H")]
        led = Suit.HEARTS
        idx = winning_card_index(trick, trump, led)
        assert idx == 2  # North's 3♣ (trump) wins


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-TRICK GAME SIMULATION (end-to-end sanity)
# ═══════════════════════════════════════════════════════════════════════════════

def _greedy_play(hand: list[Card], led_suit, trump: Suit, winning: bool) -> Card:
    """
    Ultra-simple greedy play for simulation tests only.
    Declarer team: play highest legal card.
    Defenders: play lowest legal card (so declarer wins).
    """
    plays = legal_plays(hand, led_suit, trump)
    plays_sorted = sorted(plays, key=lambda c: card_rank_in_context(c, trump, led_suit or Suit.HEARTS))
    return plays_sorted[-1] if winning else plays_sorted[0]


class TestFullGameSimulation:

    def test_exactly_11_tricks_played(self):
        """Deal and simulate a full 11-trick game; verify trick count."""
        rng = random.Random(7)
        hands_orig, kitty = deal(rng)
        trump = Suit.HEARTS
        hands = [list(h) for h in hands_orig]

        leader = SOUTH
        tricks_won = [0, 0, 0, 0]

        for trick_num in range(11):
            trick_cards = []
            led_suit = None

            for i in range(4):
                seat = (leader + i) % 4
                card = _greedy_play(hands[seat], led_suit, trump, is_declarer_team(seat))
                if i == 0:
                    led_suit = get_led_suit(card, trump)
                trick_cards.append(card)
                hands[seat].remove(card)

            winner = winning_seat(trick_cards, trump, led_suit, leader)
            tricks_won[winner] += 1
            leader = winner

        assert sum(tricks_won) == 11
        assert all(len(h) == 0 for h in hands)

    def test_tricks_split_between_teams(self):
        """Declarer + partner tricks + opponent tricks always = 11."""
        rng = random.Random(42)
        hands_orig, kitty = deal(rng)
        trump = Suit.SPADES
        hands = [list(h) for h in hands_orig]

        leader = SOUTH
        declarer_tricks = 0
        opponent_tricks = 0

        for _ in range(11):
            trick_cards = []
            led_suit = None

            for i in range(4):
                seat = (leader + i) % 4
                card = _greedy_play(hands[seat], led_suit, trump, is_declarer_team(seat))
                if i == 0:
                    led_suit = get_led_suit(card, trump)
                trick_cards.append(card)
                hands[seat].remove(card)

            winner = winning_seat(trick_cards, trump, led_suit, leader)
            if is_declarer_team(winner):
                declarer_tricks += 1
            else:
                opponent_tricks += 1
            leader = winner

        assert declarer_tricks + opponent_tricks == 11

    def test_no_card_played_twice(self):
        """Every card played across 11 tricks is unique."""
        rng = random.Random(99)
        hands_orig, kitty = deal(rng)
        trump = Suit.DIAMONDS
        hands = [list(h) for h in hands_orig]

        leader = SOUTH
        all_played = []

        for _ in range(11):
            trick_cards = []
            led_suit = None

            for i in range(4):
                seat = (leader + i) % 4
                card = _greedy_play(hands[seat], led_suit, trump, is_declarer_team(seat))
                if i == 0:
                    led_suit = get_led_suit(card, trump)
                trick_cards.append(card)
                hands[seat].remove(card)

            winner = winning_seat(trick_cards, trump, led_suit, leader)
            all_played.extend(trick_cards)
            leader = winner

        assert len(all_played) == 44   # 4 players × 11 tricks
        assert len(set(all_played)) == 44  # all unique

    def test_winner_always_has_played_card(self):
        """
        The winning card index always points to a card that is at least as
        strong as every other card in the trick.
        """
        rng = random.Random(5)
        for _ in range(20):
            hands_orig, kitty = deal(rng)
            trump = rng.choice([Suit.SPADES, Suit.CLUBS, Suit.HEARTS, Suit.DIAMONDS])
            hands = [list(h) for h in hands_orig]
            leader = SOUTH

            for _ in range(11):
                trick_cards = []
                led_suit = None
                for i in range(4):
                    seat = (leader + i) % 4
                    card = _greedy_play(hands[seat], led_suit, trump, True)
                    if i == 0:
                        led_suit = get_led_suit(card, trump)
                    trick_cards.append(card)
                    hands[seat].remove(card)

                winner_idx = winning_card_index(trick_cards, trump, led_suit)
                winner_rank = card_rank_in_context(trick_cards[winner_idx], trump, led_suit)
                for card in trick_cards:
                    assert card_rank_in_context(card, trump, led_suit) <= winner_rank


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_all_same_suit_no_trump(self):
        # All cards same non-trump suit: highest wins
        trump = Suit.SPADES
        trick = [c("9", "H"), c("J", "H"), c("A", "H"), c("3", "H")]
        assert winning_card_index(trick, trump, Suit.HEARTS) == 2  # A♥

    def test_single_trump_wins_over_all_led_suit(self):
        trump = Suit.CLUBS
        trick = [c("A", "H"), c("K", "H"), c("4", "C"), c("Q", "H")]
        # 4♣ (trump) wins even over A♥
        assert winning_card_index(trick, trump, Suit.HEARTS) == 2

    def test_joker_leads_nt_declared_suit_wins(self):
        # Joker leads in NT, declares diamonds.
        # Other players follow diamonds. Joker wins.
        led = Suit.DIAMONDS
        trick = [JOKER, c("A", "D"), c("K", "D"), c("Q", "D")]
        assert winning_card_index(trick, Suit.NO_TRUMP, led) == 0  # joker

    def test_right_bower_beats_left_bower_beats_ace(self):
        trump = Suit.SPADES
        trick = [c("A", "S"), c("J", "C"), c("J", "S"), c("K", "S")]
        # J♠ (right bower) > J♣ (left bower) > A♠ > K♠
        idx = winning_card_index(trick, trump, Suit.SPADES)
        assert idx == 2  # J♠ right bower

    def test_left_bower_beats_ace_of_trump(self):
        trump = Suit.HEARTS
        trick = [c("A", "H"), c("J", "D"), c("K", "H"), c("Q", "H")]
        # J♦ is left bower of hearts (same color = red)
        idx = winning_card_index(trick, trump, Suit.HEARTS)
        assert idx == 1  # J♦ left bower

    def test_nt_no_bowers_j_is_just_jack(self):
        # In NT, J♠ is just an 11-value spades card; no special bower status
        trick = [c("J", "S"), c("A", "S"), c("K", "S"), c("Q", "S")]
        idx = winning_card_index(trick, Suit.NO_TRUMP, Suit.SPADES)
        assert idx == 1  # A♠ wins (14 > 11)

    def test_legal_plays_on_lead_is_full_hand(self):
        hand = [c("A", "S"), c("K", "H"), JOKER, c("5", "D")]
        assert set(legal_plays(hand, None, Suit.CLUBS)) == set(hand)

    def test_get_led_suit_left_bower_lead(self):
        # J♣ leads with spades trump → led suit is spades
        led = get_led_suit(c("J", "C"), Suit.SPADES)
        assert led == Suit.SPADES
        # Other players must follow spades

    def test_left_bower_scores_as_trump_when_natural_suit_led(self):
        # J♣ = left bower of Spades. Even if Clubs is led, J♣ must score as
        # trump (115), not as a regular club (11). Otherwise it would wrongly
        # lose to A♣ (14) instead of beating it.
        jc = Card(suit=Suit.CLUBS, rank=Rank.JACK)
        score = card_rank_in_context(jc, Suit.SPADES, Suit.CLUBS)
        ace_clubs = card_rank_in_context(Card(suit=Suit.CLUBS, rank=Rank.ACE), Suit.SPADES, Suit.CLUBS)
        assert score == 115            # trump scale, not led-suit scale
        assert score > ace_clubs       # left bower beats A♣ even when clubs led

    def test_left_bower_not_in_following_when_natural_suit_led(self):
        # J♣ (left bower of Spades) must NOT be playable to follow Clubs —
        # it's trump. Only real clubs follow.
        hand = [Card(suit=Suit.CLUBS, rank=Rank.JACK),   # left bower
                Card(suit=Suit.CLUBS, rank=Rank.FIVE)]   # real club
        plays = legal_plays(hand, Suit.CLUBS, Suit.SPADES)
        assert Card(suit=Suit.CLUBS, rank=Rank.FIVE) in plays
        assert Card(suit=Suit.CLUBS, rank=Rank.JACK) not in plays  # must not play bower as club

    def test_get_led_suit_joker_leads_trump_contract(self):
        led = get_led_suit(JOKER, Suit.HEARTS)
        assert led == Suit.HEARTS

    def test_deck_covers_all_cards_used_in_deal(self):
        deck = set(build_deck())
        rng = random.Random(1)
        for _ in range(10):
            hands, kitty = deal(rng)
            dealt = set(c for h in hands for c in h) | set(kitty)
            assert dealt == deck


# ═══════════════════════════════════════════════════════════════════════════════
# CONTRACT CLASS — NULLO / DOUBLE NULLO GAME LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

class TestContract:

    # ── Normal contract ───────────────────────────────────────────────────────

    def test_normal_all_four_seats_active(self):
        contract = Contract(bid=Bid(7, BidSuit.HEARTS), declarer=SOUTH)
        assert contract.active_seats == (0, 1, 2, 3)

    def test_normal_partner_is_opposite(self):
        contract = Contract(bid=Bid(7, BidSuit.HEARTS), declarer=SOUTH)
        assert contract.partner == NORTH  # (2+2)%4 = 0

    def test_normal_declarer_side_includes_partner(self):
        contract = Contract(bid=Bid(7, BidSuit.HEARTS), declarer=SOUTH)
        assert contract.is_declarer_side(SOUTH)
        assert contract.is_declarer_side(NORTH)
        assert not contract.is_declarer_side(EAST)
        assert not contract.is_declarer_side(WEST)

    def test_normal_made_contract(self):
        contract = Contract(bid=Bid(7, BidSuit.HEARTS), declarer=SOUTH)
        assert contract.made_contract(7)
        assert contract.made_contract(8)
        assert not contract.made_contract(6)

    def test_normal_tricks_needed(self):
        assert Contract(bid=Bid(8, BidSuit.SPADES), declarer=SOUTH).tricks_needed() == 8

    def test_normal_trump(self):
        contract = Contract(bid=Bid(7, BidSuit.CLUBS), declarer=SOUTH)
        assert contract.trump == Suit.CLUBS

    # ── Nullo ────────────────────────────────────────────────────────────────

    def test_nullo_partner_sits_out(self):
        contract = Contract(bid=NULLO, declarer=SOUTH)
        # North (partner) sits out → only East, South, West play
        assert NORTH not in contract.active_seats
        assert contract.active_seats == (1, 2, 3)

    def test_nullo_three_active_seats(self):
        contract = Contract(bid=NULLO, declarer=SOUTH)
        assert len(contract.active_seats) == 3

    def test_nullo_partner_not_declarer_side(self):
        # In regular Nullo, only the declarer counts — partner is inactive
        contract = Contract(bid=NULLO, declarer=SOUTH)
        assert contract.is_declarer_side(SOUTH)
        assert not contract.is_declarer_side(NORTH)   # sits out
        assert not contract.is_declarer_side(EAST)
        assert not contract.is_declarer_side(WEST)

    def test_nullo_made_when_zero_tricks(self):
        contract = Contract(bid=NULLO, declarer=SOUTH)
        assert contract.made_contract(0)
        assert not contract.made_contract(1)

    def test_nullo_trump_is_none(self):
        assert Contract(bid=NULLO, declarer=SOUTH).trump is None

    def test_nullo_tricks_needed_zero(self):
        assert Contract(bid=NULLO, declarer=SOUTH).tricks_needed() == 0

    def test_nullo_partner_sits_out_east_declarer(self):
        # East (1) declares nullo → West (3) sits out
        contract = Contract(bid=NULLO, declarer=EAST)
        assert contract.partner == WEST
        assert WEST not in contract.active_seats
        assert contract.active_seats == (0, 1, 2)

    # ── Double Nullo ─────────────────────────────────────────────────────────

    def test_double_nullo_all_four_play(self):
        contract = Contract(bid=DOUBLE_NULLO, declarer=SOUTH)
        assert contract.active_seats == (0, 1, 2, 3)

    def test_double_nullo_both_partners_on_declarer_side(self):
        contract = Contract(bid=DOUBLE_NULLO, declarer=SOUTH)
        assert contract.is_declarer_side(SOUTH)
        assert contract.is_declarer_side(NORTH)   # partner plays and tries to lose
        assert not contract.is_declarer_side(EAST)
        assert not contract.is_declarer_side(WEST)

    def test_double_nullo_made_when_zero_tricks(self):
        contract = Contract(bid=DOUBLE_NULLO, declarer=SOUTH)
        assert contract.made_contract(0)
        assert not contract.made_contract(1)


# ═══════════════════════════════════════════════════════════════════════════════
# play_order() AND winning_seat() WITH NULLO
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlayOrderAndNullo:

    def test_play_order_standard_south_leads(self):
        assert play_order(SOUTH) == [2, 3, 0, 1]  # S, W, N, E

    def test_play_order_standard_north_leads(self):
        assert play_order(NORTH) == [0, 1, 2, 3]  # N, E, S, W

    def test_play_order_standard_west_leads(self):
        assert play_order(WEST) == [3, 0, 1, 2]   # W, N, E, S

    def test_play_order_nullo_north_sits_out_south_leads(self):
        # Active seats: East(1), South(2), West(3). South leads.
        order = play_order(SOUTH, (1, 2, 3))
        assert order == [2, 3, 1]   # S → W → E (skip North)

    def test_play_order_nullo_north_sits_out_west_leads(self):
        order = play_order(WEST, (1, 2, 3))
        assert order == [3, 1, 2]   # W → E → S (skip North)

    def test_play_order_nullo_north_sits_out_east_leads(self):
        order = play_order(EAST, (1, 2, 3))
        assert order == [1, 2, 3]   # E → S → W (skip North)

    def test_winning_seat_int_shortcut_still_works(self):
        # Passing an int should behave identically to before (4-player)
        trump = Suit.HEARTS
        trick = [c("5", "H"), c("A", "H"), c("K", "H"), c("Q", "H")]
        # South(2) leads; A♥ at index 1 played by West(3)
        assert winning_seat(trick, trump, Suit.HEARTS, SOUTH) == WEST

    def test_winning_seat_with_explicit_seats_4player(self):
        trump = Suit.HEARTS
        trick = [c("5", "H"), c("A", "H"), c("K", "H"), c("Q", "H")]
        seats = play_order(SOUTH)       # [2, 3, 0, 1]
        assert winning_seat(trick, trump, Suit.HEARTS, seats) == WEST   # idx 1 → seat 3

    def test_winning_seat_nullo_3player(self):
        # Nullo: North sits out. South(2) leads. Order: [S, W, E] = [2, 3, 1].
        # East plays the highest card (A♥ at index 2 in trick).
        trump = Suit.NO_TRUMP   # Nullo has no trump
        led = Suit.HEARTS
        trick = [c("5", "H"), c("K", "H"), c("A", "H")]  # S, W, E cards
        seats = play_order(SOUTH, (1, 2, 3))   # [2, 3, 1]
        winner = winning_seat(trick, trump, led, seats)
        assert winner == EAST   # A♥ at index 2 → seats[2] = 1 = East

    def test_winning_seat_nullo_3player_west_leads(self):
        # West(3) leads. Order: [W, E, S] = [3, 1, 2]. South wins.
        led = Suit.SPADES
        trick = [c("4", "S"), c("5", "S"), c("A", "S")]  # W, E, S
        seats = play_order(WEST, (1, 2, 3))   # [3, 1, 2]
        winner = winning_seat(trick, Suit.NO_TRUMP, led, seats)
        assert winner == SOUTH   # A♠ at index 2 → seats[2] = 2 = South

    def test_nullo_3player_full_trick_loop(self):
        """Simulate 11 Nullo tricks (3-player). Verify total = 11 and no North."""
        rng = random.Random(13)
        hands_orig, kitty = deal(rng)
        contract = Contract(bid=NULLO, declarer=SOUTH)
        active = contract.active_seats   # (1, 2, 3) — no North

        # Give North's cards nowhere to go; only active seats play
        hands = {s: list(hands_orig[s]) for s in active}

        leader = SOUTH
        tricks_per_seat = {s: 0 for s in active}

        for _ in range(11):
            seats_this_trick = play_order(leader, active)
            trick_cards = []
            led_suit = None

            for seat in seats_this_trick:
                # Simple: play first legal card
                card = legal_plays(hands[seat], led_suit, Suit.NO_TRUMP)[0]
                if led_suit is None:
                    led_suit = get_led_suit(card, Suit.NO_TRUMP,
                                           nt_declared_suit=Suit.HEARTS)
                trick_cards.append(card)
                hands[seat].remove(card)

            winner = winning_seat(trick_cards, Suit.NO_TRUMP, led_suit, seats_this_trick)
            tricks_per_seat[winner] += 1
            leader = winner

        assert sum(tricks_per_seat.values()) == 11
        assert NORTH not in tricks_per_seat   # North never wins a trick
