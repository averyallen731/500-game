"""
Single-Observer Information Set Monte Carlo Tree Search (SO-ISMCTS) for 500.

The tree is built from the root seat's perspective. Each iteration:
  1. Samples a consistent world (determinisation)
  2. Traverses the shared tree (selection + expansion)
  3. Plays out the rest with a rollout policy
  4. Backpropagates the reward

The rollout policy is a parameter — defaults to the heuristic but can be
swapped for any function with the same signature as heuristic.play_card().
Improving the heuristic automatically improves ISMCTS rollout quality.

Public API
----------
run_ismcts(root_seat, root_hand, played_cards, trick_so_far,
           trick_seats_so_far, contract, trump, leader,
           dec_tricks_so_far, tricks_done, rng,
           iterations, time_budget_s, rollout_fn) -> Card
"""
from __future__ import annotations

import math
import random
import time
from typing import Callable, Optional

from backend.game.cards import Card, Suit
from backend.game.bidding import Contract
from backend.game.tricks import legal_plays, play_order as _play_order
from backend.solver.ismcts_state import ISMCTSState, sample_world, _nt_joker_led_suit
from backend.solver.heuristic import play_card as _default_rollout

# Rollout policy signature matches heuristic.play_card()
RolloutFn = Callable[
    [int, list[Card], list[Card], int, Optional[Suit], Suit, Contract, set[Card], random.Random],
    Card,
]

_C       = 1.4   # UCB exploration constant (tune: lower = exploit, higher = explore)
_EPSILON = 0.1   # fraction of random moves in rollouts (diversity / anti-collapse)


# ── Tree node ─────────────────────────────────────────────────────────────────

class ISNode:
    """
    Node in the SO-ISMCTS tree.

    SO-ISMCTS key difference from plain MCTS: actions may not be available
    in every determinisation.  `availability` tracks how many times an
    action was legal (available) when its parent was visited — the UCB
    denominator uses availability rather than parent visit count.
    """
    __slots__ = (
        "parent", "incoming_action", "acting_seat",
        "children", "visits", "total_reward", "availability",
        "_seen_availability",
    )

    def __init__(
        self,
        parent: Optional[ISNode],
        incoming_action: Optional[Card],
        acting_seat: int,
    ) -> None:
        self.parent = parent
        self.incoming_action = incoming_action
        self.acting_seat = acting_seat
        self.children: dict[Card, ISNode] = {}
        self.visits: int = 0
        self.total_reward: float = 0.0
        self.availability: int = 0
        # SO-ISMCTS: track availability for ALL legal actions seen at this node,
        # including those not yet expanded.  When a child is created, its
        # availability is initialised from this counter so no visits are missed.
        self._seen_availability: dict[Card, int] = {}

    def visit(self, legal: list[Card], rng: random.Random) -> tuple[ISNode, Card, bool]:
        """
        SO-ISMCTS combined selection + expansion for one iteration.

        1. Increment availability for EVERY legal action (SO-ISMCTS rule),
           whether or not a child node exists yet.
        2. If any legal action has no child yet, expand one at random;
           initialise its availability from the running counter.
        3. Otherwise, UCB-select among legal children.

        Returns (child, action, was_newly_expanded).
        """
        # Step 1: increment availability for ALL legal actions at this node
        for card in legal:
            self._seen_availability[card] = self._seen_availability.get(card, 0) + 1
            if card in self.children:
                self.children[card].availability += 1

        # Step 2: expansion
        untried = [c for c in legal if c not in self.children]
        if untried:
            action = rng.choice(untried)
            child = ISNode(parent=self, incoming_action=action, acting_seat=-1)
            # Seed availability with how many times this action was already legal
            child.availability = self._seen_availability.get(action, 1)
            self.children[action] = child
            return child, action, True

        # Step 3: UCB selection among legal children
        def ucb(card: Card) -> float:
            ch = self.children[card]
            exploit = ch.total_reward / ch.visits
            explore  = _C * math.sqrt(math.log(max(ch.availability, 1)) / ch.visits)
            return exploit + explore

        best = max(legal, key=ucb)
        return self.children[best], best, False

    def update(self, reward: float) -> None:
        self.visits += 1
        self.total_reward += reward

    def best_action(self, legal: list[Card]) -> Optional[Card]:
        """Most-visited child among currently legal actions (robust child selection)."""
        legal_set = set(legal)
        candidates = [(card, ch) for card, ch in self.children.items()
                      if card in legal_set and ch.visits > 0]
        if not candidates:
            return None
        return max(candidates, key=lambda x: x[1].visits)[0]


# ── Public entry point ────────────────────────────────────────────────────────

def run_ismcts(
    root_seat: int,
    root_hand: list[Card],
    played_cards: set[Card],
    trick_so_far: list[Card],
    trick_seats_so_far: list[int],
    contract: Contract,
    trump: Suit,
    leader: int,
    dec_tricks_so_far: int,
    tricks_done: int,
    rng: random.Random,
    iterations: int = 500,
    time_budget_s: Optional[float] = 0.5,
    rollout_fn: RolloutFn = _default_rollout,
) -> Card:
    """
    Run SO-ISMCTS and return the best card for root_seat to play.

    Parameters
    ----------
    root_seat          : the seat making the decision
    root_hand          : root_seat's current hand (cards already played removed)
    played_cards       : cards played in completed tricks (public)
    trick_so_far       : cards played so far in the current trick (public)
    trick_seats_so_far : seat that played each card in trick_so_far (parallel)
    contract           : the current contract
    trump              : effective trump suit (Suit.NO_TRUMP for nullo/NT)
    leader             : seat that led the current trick
    dec_tricks_so_far  : tricks won by declaring side in completed tricks
    tricks_done        : number of completed tricks
    rng                : random number generator (for reproducibility / seeding)
    iterations         : maximum ISMCTS iterations (wall-clock budget takes priority)
    time_budget_s      : hard wall-clock limit in seconds (None = no limit)
    rollout_fn         : card-play policy for rollouts; must have the same
                         signature as heuristic.play_card().  Swap freely —
                         the tree logic is completely independent of this.
    """
    root = ISNode(parent=None, incoming_action=None, acting_seat=root_seat)
    deadline = time.monotonic() + time_budget_s if time_budget_s else None

    for _ in range(iterations):
        if deadline and time.monotonic() > deadline:
            break

        # ── 1. Determinise ────────────────────────────────────────────────────
        hands = sample_world(
            root_seat, root_hand, played_cards,
            trick_so_far, trick_seats_so_far, contract, rng,
        )

        # ── 2. Construct state for this determinisation ───────────────────────
        state = ISMCTSState(
            hands=hands,
            contract=contract,
            trump=trump,
            leader=leader,
            tricks_done=tricks_done,
            dec_tricks=dec_tricks_so_far,
            trick=list(trick_so_far),
            played=set(played_cards),
            _order=_play_order(leader, contract.active_seats),
        )

        # ── 3. Selection + Expansion ──────────────────────────────────────────
        node = root
        path: list[ISNode] = []

        while not state.is_terminal():
            legal = state.legal()
            if not legal:
                break

            child, action, expanded = node.visit(legal, rng)
            child.acting_seat = state.current_seat
            path.append(child)
            state.apply(action)
            node = child

            if expanded:
                break  # hand off to rollout from the newly expanded node

        # ── 4. Rollout ────────────────────────────────────────────────────────
        _rollout(state, contract, trump, rng, rollout_fn)

        # ── 5. Backpropagate ──────────────────────────────────────────────────
        reward = state.reward(root_seat)
        for n in path:
            n.update(reward)

    # ── Final move selection ──────────────────────────────────────────────────
    # Determine actual led suit from the real (non-sampled) state
    led = _compute_led_suit(trick_so_far, trump, root_hand)
    actual_legal = legal_plays(root_hand, led, trump)

    best = root.best_action(actual_legal)
    if best is None:
        # No iterations completed or all children have 0 visits — fall back
        return rollout_fn(
            root_seat, root_hand, trick_so_far, leader,
            led, trump, contract, played_cards, rng,
        )
    return best


# ── Internal helpers ──────────────────────────────────────────────────────────

def _rollout(
    state: ISMCTSState,
    contract: Contract,
    trump: Suit,
    rng: random.Random,
    rollout_fn: RolloutFn,
) -> None:
    """Play out remaining tricks to terminal using rollout_fn + epsilon-random."""
    while not state.is_terminal():
        seat  = state.current_seat
        legal = state.legal()
        if not legal:
            break

        if rng.random() < _EPSILON:
            card = rng.choice(legal)
        else:
            try:
                card = rollout_fn(
                    seat,
                    state.hands[seat],
                    state.trick,
                    state.leader,
                    state.led_suit,
                    trump,
                    contract,
                    state.played,
                    rng,
                )
                if card not in legal:
                    card = rng.choice(legal)   # safety net
            except Exception:
                card = rng.choice(legal)

        state.apply(card)


def _compute_led_suit(
    trick_so_far: list[Card],
    trump: Suit,
    leader_hand: list[Card],
) -> Optional[Suit]:
    """Derive the effective led suit from what's visible, handling NT joker edge-case."""
    if not trick_so_far:
        return None
    lead = trick_so_far[0]
    if lead.is_joker() and trump == Suit.NO_TRUMP:
        return _nt_joker_led_suit(leader_hand)
    return lead.effective_suit(trump)
