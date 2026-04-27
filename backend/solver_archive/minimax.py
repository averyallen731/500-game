"""
Fail-soft alpha-beta minimax double-dummy solver for 500.

State is encoded as bitmasks per seat.  The transposition table maps
(hand0, hand1, hand2, hand3, trick_tuple, next_seat) -> (lo, hi, depth).

trick_tuple: sequence of (seat, card_id) pairs for cards already played
in the current trick.  When the joker leads in NT a fifth element
(seat, card_id, declared_suit_index) is stored for the lead entry.

Declaring side tries to MAXIMISE declarer tricks in normal contracts;
for nullo/double-nullo both declaring seats try to MINIMISE.
"""
from typing import Optional

from backend.game.cards import Card, Suit, JOKER, card_rank_in_context
from backend.game.tricks import legal_plays, play_order, winning_seat, get_led_suit
from backend.game.bidding import Contract
from backend.solver.card_map import CARD_TO_ID, ID_TO_CARD, hand_to_mask, mask_to_cards


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

# Map Suit enum to a small int for compact storage in trick tuples
_SUIT_TO_IDX: dict[Optional[Suit], int] = {
    Suit.SPADES: 0,
    Suit.CLUBS: 1,
    Suit.HEARTS: 2,
    Suit.DIAMONDS: 3,
    Suit.NO_TRUMP: 4,
    None: 5,
}
_IDX_TO_SUIT: dict[int, Optional[Suit]] = {v: k for k, v in _SUIT_TO_IDX.items()}

# All four plain suits used when branching joker-in-NT leads
_PLAIN_SUITS = (Suit.SPADES, Suit.CLUBS, Suit.HEARTS, Suit.DIAMONDS)


def _is_max_node(seat: int, contract: Contract) -> bool:
    """
    Returns True if this seat should try to MAXIMISE declarer tricks.
    Declaring side maximises in normal contracts; MINIMISES in nullo.
    Opponents always want to minimise declarer tricks.
    """
    on_declaring_side = contract.is_declarer_side(seat)
    if contract.bid.is_nullo or contract.bid.is_double_nullo:
        # Declaring side tries to take ZERO tricks → they minimise
        return not on_declaring_side
    return on_declaring_side


def _get_led_suit_from_trick(
    current_trick: tuple,
    trump: Optional[Suit],
) -> Optional[Suit]:
    """
    Extract the effective led suit from the current trick tuple.
    Returns None if the trick is empty (player is leading).

    trick tuple entries are (seat, card_id) pairs, except the first entry
    when the joker leads in NT — that entry is (seat, card_id, suit_idx).
    """
    if not current_trick:
        return None
    lead_entry = current_trick[0]
    lead_card_id = lead_entry[1]
    lead_card = ID_TO_CARD[lead_card_id]
    effective_trump = trump if trump is not None else Suit.NO_TRUMP
    if lead_card.is_joker() and effective_trump == Suit.NO_TRUMP:
        # Declared suit is stored as the third element of the lead entry
        suit_idx = lead_entry[2]
        return _IDX_TO_SUIT[suit_idx]
    return lead_card.effective_suit(effective_trump)


# --------------------------------------------------------------------------- #
# Transposition table
# --------------------------------------------------------------------------- #

class TranspositionTable:
    """
    Maps state_key -> (lower_bound, upper_bound, depth).
    Depth-preferred replacement: only update if new_depth >= stored depth.
    """

    def __init__(self):
        self._table: dict = {}

    def lookup(
        self,
        key,
        alpha: int,
        beta: int,
    ) -> Optional[tuple[int, int, int, int]]:
        """
        Returns (lo, hi, depth, adjusted_alpha, adjusted_beta) if a useful
        entry exists, else None.

        Actually returns (lo, hi, new_alpha, new_beta) where new_alpha/beta
        are tightened bounds.  Caller should return lo if lo >= beta, or hi
        if hi <= alpha.
        """
        entry = self._table.get(key)
        if entry is None:
            return None
        lo, hi, _depth = entry
        new_alpha = max(alpha, lo)
        new_beta = min(beta, hi)
        return lo, hi, new_alpha, new_beta

    def store(self, key, lo: int, hi: int, depth: int) -> None:
        existing = self._table.get(key)
        if existing is None or depth >= existing[2]:
            self._table[key] = (lo, hi, depth)

    def clear(self) -> None:
        self._table.clear()


# --------------------------------------------------------------------------- #
# Equivalence reduction
# --------------------------------------------------------------------------- #

def _reduce_moves(
    moves: list[Card],
    seat: int,
    hands_masks: list[int],
    effective_trump: Suit,
    sort_led: Suit,
) -> list[Card]:
    """
    Equivalence reduction: within the same effective suit, two cards held by
    the same player are interchangeable if no opponent holds any card ranked
    between them.  We keep only the highest representative of each such group.

    Example: South holds A♥ K♥ Q♥ and no opponent has J♥ or 10♥ etc.
    between them → only try A♥ (K♥ and Q♥ lead to identical future trees).

    Cards of different suits, the joker, and cards where opponents DO hold
    an intermediate rank are all kept as distinct moves.
    """
    if len(moves) <= 1:
        return moves

    # Build set of ranks-in-context held by opponents, grouped by effective suit
    opp_ranks: dict = {}   # effective_suit_idx -> set of int ranks
    for s in range(4):
        if s == seat:
            continue
        tmp = hands_masks[s]
        while tmp:
            lsb = tmp & (-tmp)
            cid = lsb.bit_length() - 1
            card = ID_TO_CARD[cid]
            eff = card.effective_suit(effective_trump)
            r = card_rank_in_context(card, effective_trump, sort_led)
            key = _SUIT_TO_IDX.get(eff, 6)
            if key not in opp_ranks:
                opp_ranks[key] = set()
            opp_ranks[key].add(r)
            tmp ^= lsb

    # Group moves by effective suit
    suit_groups: dict = {}
    jokers = []
    for card in moves:
        if card.is_joker():
            jokers.append(card)
            continue
        eff = card.effective_suit(effective_trump)
        key = _SUIT_TO_IDX.get(eff, 6)
        if key not in suit_groups:
            suit_groups[key] = []
        suit_groups[key].append(card)

    result = list(jokers)
    for key, group in suit_groups.items():
        # Already sorted descending by rank from earlier move ordering
        opp = opp_ranks.get(key, set())
        kept = [group[0]]
        for i in range(1, len(group)):
            prev_rank = card_rank_in_context(group[i - 1], effective_trump, sort_led)
            curr_rank = card_rank_in_context(group[i], effective_trump, sort_led)
            # Keep this card only if an opponent has something ranked between it and prev
            if any(curr_rank < r < prev_rank for r in opp):
                kept.append(group[i])
            # else: equivalent to the card above — skip
        result.extend(kept)

    return result


# --------------------------------------------------------------------------- #
# Core minimax
# --------------------------------------------------------------------------- #

def _minimax(
    hands_masks: list[int],   # bitmask per seat; modified in place temporarily
    current_trick: tuple,     # (seat, card_id) pairs played so far this trick
    next_seat: int,
    tricks_remaining: int,
    contract: Contract,
    alpha: int,
    beta: int,
    tt: TranspositionTable,
    active_seats: tuple[int, ...],
    trump: Optional[Suit],
) -> int:
    """
    Returns the number of tricks the declaring side wins from THIS POSITION
    ONWARD (relative, not including past accumulated tricks).

    Removing `declarer_tricks` from the signature fixes the TT bug: the TT
    now stores relative values that are valid regardless of how many tricks
    have already been won, so positions reached via different paths correctly
    reuse cached results.
    """
    # ---- Terminal: no tricks left ----------------------------------------- #
    if tricks_remaining == 0 and not current_trick:
        return 0  # no more tricks to win from here

    # ---- Transposition table lookup --------------------------------------- #
    state_key = (
        hands_masks[0], hands_masks[1], hands_masks[2], hands_masks[3],
        current_trick, next_seat,
    )
    tt_result = tt.lookup(state_key, alpha, beta)
    if tt_result is not None:
        lo, hi, new_alpha, new_beta = tt_result
        if lo >= beta:
            return lo
        if hi <= alpha:
            return hi
        alpha, beta = new_alpha, new_beta

    orig_alpha = alpha
    orig_beta = beta

    # ---- Determine led suit ------------------------------------------------ #
    led_suit = _get_led_suit_from_trick(current_trick, trump)
    effective_trump = trump if trump is not None else Suit.NO_TRUMP

    # ---- Legal moves for next_seat ---------------------------------------- #
    hand_cards = mask_to_cards(hands_masks[next_seat])
    moves = legal_plays(hand_cards, led_suit, effective_trump)

    sort_led = led_suit if led_suit is not None else Suit.NO_TRUMP
    moves.sort(key=lambda c: card_rank_in_context(c, effective_trump, sort_led), reverse=True)
    moves = _reduce_moves(moves, next_seat, hands_masks, effective_trump, sort_led)

    is_max = _is_max_node(next_seat, contract)

    # Joker-in-NT: split into normal moves and joker-lead branches
    if not current_trick and effective_trump == Suit.NO_TRUMP:
        joker_move_list = [m for m in moves if m.is_joker()]
        moves = [m for m in moves if not m.is_joker()]
    else:
        joker_move_list = []

    # ---- Search ------------------------------------------------------------ #
    if is_max:
        best = -1
        for card in moves:
            result = _make_move_and_recurse(
                card, None, next_seat, hands_masks, current_trick,
                tricks_remaining, contract, alpha, beta, tt, active_seats, trump,
            )
            if result > best:
                best = result
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        for card in joker_move_list:
            for declared_suit in _PLAIN_SUITS:
                result = _make_move_and_recurse(
                    card, declared_suit, next_seat, hands_masks, current_trick,
                    tricks_remaining, contract, alpha, beta, tt, active_seats, trump,
                )
                if result > best:
                    best = result
                alpha = max(alpha, best)
                if alpha >= beta:
                    break
            if alpha >= beta:
                break
    else:
        best = 12
        for card in moves:
            result = _make_move_and_recurse(
                card, None, next_seat, hands_masks, current_trick,
                tricks_remaining, contract, alpha, beta, tt, active_seats, trump,
            )
            if result < best:
                best = result
            beta = min(beta, best)
            if alpha >= beta:
                break
        for card in joker_move_list:
            for declared_suit in _PLAIN_SUITS:
                result = _make_move_and_recurse(
                    card, declared_suit, next_seat, hands_masks, current_trick,
                    tricks_remaining, contract, alpha, beta, tt, active_seats, trump,
                )
                if result < best:
                    best = result
                beta = min(beta, best)
                if alpha >= beta:
                    break
            if alpha >= beta:
                break

    # ---- Store in TT ------------------------------------------------------- #
    depth = tricks_remaining + (1 if current_trick else 0)
    if best <= orig_alpha:
        tt.store(state_key, -1, best, depth)
    elif best >= orig_beta:
        tt.store(state_key, best, 12, depth)
    else:
        tt.store(state_key, best, best, depth)

    return best


def _make_move_and_recurse(
    card: Card,
    declared_suit: Optional[Suit],
    seat: int,
    hands_masks: list[int],
    current_trick: tuple,
    tricks_remaining: int,
    contract: Contract,
    alpha: int,
    beta: int,
    tt: TranspositionTable,
    active_seats: tuple[int, ...],
    trump: Optional[Suit],
) -> int:
    """Play `card` for `seat`, recurse, then restore the hand mask."""
    card_id = CARD_TO_ID[card]

    # Build new trick tuple
    if not current_trick and declared_suit is not None:
        new_trick = ((seat, card_id, _SUIT_TO_IDX[declared_suit]),)
    else:
        new_trick = current_trick + ((seat, card_id),)

    # Remove card from hand
    old_mask = hands_masks[seat]
    hands_masks[seat] = old_mask ^ (1 << card_id)

    if len(new_trick) == len(active_seats):
        # Trick complete — resolve winner
        trick_cards = [ID_TO_CARD[entry[1]] for entry in new_trick]
        playing_seats_list = [entry[0] for entry in new_trick]
        effective_trump = trump if trump is not None else Suit.NO_TRUMP
        led_suit = _get_led_suit_from_trick(new_trick, trump)
        winner = winning_seat(trick_cards, effective_trump, led_suit, playing_seats_list)

        # This trick's contribution + all future tricks
        delta = 1 if contract.is_declarer_side(winner) else 0
        result = delta + _minimax(
            hands_masks, (), winner,
            tricks_remaining - 1, contract, alpha - delta, beta - delta,
            tt, active_seats, trump,
        )
    else:
        # Trick in progress — advance to next seat
        order = play_order(new_trick[0][0], active_seats)
        next_seat = order[len(new_trick)]
        result = _minimax(
            hands_masks, new_trick, next_seat,
            tricks_remaining, contract, alpha, beta,
            tt, active_seats, trump,
        )

    hands_masks[seat] = old_mask
    return result


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

def solve(
    hands: list[list[Card]],
    contract: Contract,
    leader: int = None,
) -> int:
    """
    Double-dummy solve.  Returns the number of tricks the declaring side wins
    with perfect play by both sides.

    hands[seat] is the list of Cards for that seat (seats 0-3).
    leader defaults to the contract declarer.
    """
    if leader is None:
        leader = contract.declarer

    active_seats = contract.active_seats
    trump = contract.trump  # None for nullo

    # Validate that leader is in active_seats
    if leader not in active_seats:
        raise ValueError(f"Leader seat {leader} is not in active_seats {active_seats}")

    # Convert hands to bitmasks
    hands_masks = [hand_to_mask(hands[s]) for s in range(4)]

    # Determine total tricks = cards per active player
    # Each active seat has the same number of cards (for a freshly dealt hand)
    n_tricks = len(hands[leader])  # should be 11

    tt = TranspositionTable()

    result = _minimax(
        hands_masks,
        (),           # empty trick at start
        leader,
        n_tricks,     # tricks remaining
        contract,
        0,            # alpha
        n_tricks + 1, # beta
        tt,
        active_seats,
        trump,
    )
    return result
