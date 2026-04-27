Avery's original prompt:

This app will simulate the game 500. 

IMPORTANT RULE CHANGES:
Follow rules in rules.txt, and wikipedia except with these important modifications:
Cards in play are 3-A red and 4-A black, one joker. Total 47 cards. 11 card hands for each of the 4 players and a 3 card kitty. One round of bidding. Bids go from 6-11 of any suit, including no trump, as well as nullo and double nullo (both partners play)

The main functionality I want right now is a bidding practice app. Show the user a hand + situation (seat, prior bids). User picks a bid. App tells them what they *should* have bid — by simulating each trump choice and showing expected tricks and EV.

---

## Current Plan (as of April 2026)

### Core insight
Expected tricks only depends on **trump choice**, not bid level. So we compute **6 trick distributions**:
- 4 suits as trump (make-tricks policy)
- NT (make-tricks policy)  
- Nullo (lose-tricks policy)

Each distribution = sample ~200 random deals, play each out with heuristic policy, collect trick counts. EV per bid = trivial arithmetic on top.

### Play policy: Heuristic (rule-based)
Python minimax was ~100s/solve — fundamentally too slow. DDS is archived (see `backend/solver_archive/`). The runtime engine is a hand-coded heuristic policy:
- Fast enough: ~1-4ms/deal → 1200 playouts (200×6) in ~2-5s total
- Symmetric bias: heuristic plays both sides, so errors partially cancel when averaging
- Quality gate: calibrate against archived DDS on cheap endgames, target ±0.5 tricks avg

### Archived DDS (DO NOT use at runtime)
`backend/solver_archive/` contains the minimax/alpha-beta/TT solver. Use only if Avery explicitly says to run a correctness check. Do not import it in the main app.

---

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, uvicorn
- **Frontend:** React (Vite), inline styles throughout (no Tailwind)

## Project Layout
```
500-game/
  backend/
    game/
      cards.py, deck.py, hand.py, tricks.py, bidding.py
    solver/
      heuristic.py     # TODO — card-play heuristic policy
      sampler.py       # TODO — sample_remaining(known_hand, rng)
      evaluator.py     # TODO — evaluate_hand(hand, seat, prior_bids) -> BidAdvice
    solver_archive/    # archived DDS — minimax.py, card_map.py, solver.py, sampler.py
    api/
      main.py, routes.py, schemas.py, game_state.py
  frontend/src/
    components/  App.jsx  ...
  tests/
    test_phase1.py, test_game_logic.py, test_solver.py (some archived tests will break — OK)
  research/            # algorithm research papers
```

## Key Rules (CONFIRMED — do not regress)
- Deck: 3–A red suits, 4–A black suits, one joker = 47 cards
- 4 players × 11-card hands + 3-card kitty
- **One round of bidding** — each player bids exactly once; highest bid wins; all pass → redeal
- **Double Nullo**: only valid if partner has ALREADY bid Nullo this round
- Nullo: declarer tries to lose ALL tricks; partner sits out (3-player trick)
- Double Nullo: BOTH partners try to lose all tricks (4-player)
- Joker: always highest card, even in Nullo
- Left bower: Jack of same color as trump — treated as trump suit card

## Scoring Rules (CONFIRMED)
- Declaring side makes contract: +bid_point_value
- Declaring side fails: −bid_point_value (no partial credit, no over-trick bonus)
- Opponents: always +10 pts per trick won regardless of contract result

## Seat convention
NORTH=0, EAST=1, SOUTH=2 (user/declarer), WEST=3

---

## Progress Log

### Phase 1 — COMPLETE ✅ (138 tests)
Files: `cards.py`, `deck.py`, `tricks.py`, `bidding.py`, `hand.py`

Key additions:
- `Contract` class — encapsulates nullo/double-nullo partner-sits-out logic, `active_seats`, `is_declarer_side()`, `made_contract()`
- `play_order(leader, active_seats)` — handles 3-player Nullo tricks correctly
- `HandAnalysis` + `best_kitty_discard()` (normal + nullo discard strategies)

### Test Webapp — COMPLETE ✅
`backend/api/` + `frontend/src/` — full playable game loop:
- 1-round bidding, Double Nullo gated on partner Nullo, invalid bids greyed out
- Scoring banner, bower sorting in hand, kitty cards highlighted gold
- Point values on bid buttons and contract display

### Phase 2 — ABANDONED (DDS too slow in Python)
Double Dummy Solver (minimax + alpha-beta + TT) was built and unit tested but benchmarked at ~100s/solve. Target was <2s. Archived in `backend/solver_archive/`. Do not resurrect without Avery asking.

### Phase 3 — IN PROGRESS (next session)
Build the heuristic play policy + bid evaluator.

**Avery's task before next session:** Research 500 heuristics (card-play strategy for normal + nullo). Ask an experienced player or find a strategy guide.

**Steps:**
1. `backend/solver/heuristic.py` — `play_card(hand, trick_so_far, contract, game_state) -> Card`
   - Make-tricks policy: lead high trumps, pull trumps, cash winners in NT, signal partner, short-suit
   - Lose-tricks policy for Nullo: play highest losing card, avoid taking tricks
2. `backend/solver/sampler.py` — `sample_remaining(known_hand, rng)` (re-implement, same API as archived version)
3. `backend/solver/evaluator.py` — `evaluate_hand(hand, seat, prior_bids, n_samples=200) -> BidAdvice`
   - BidAdvice: for each (trump, level) → avg_tricks, pct_making, ev, optimal_bid
4. Wire into FastAPI route + React result panel

**Smart pruning:** skip trump suits where user holds <3 cards; skip NT if <2 top-card equivalents; skip Nullo if any unguarded ace/king.

**Deferred to later:**
- Bid-conditioned sampling (bias samples to match prior bids)
- ISMCTS for stronger webapp bots (v2)
- RL / self-play (v3)

---

## Workflow Rules (Claude must follow these)

1. **Auto-critic subagent:** After completing any non-trivial implementation, automatically launch a subagent to criticize the code. Cross-reference rules.txt, run tests, report confirmed bugs, suspected bugs, rules gaps, test gaps.

2. **Opus for planning:** Use `claude-opus-4-7` when designing approach to a new feature. Sonnet handles implementation.

3. **Fix before feature:** If any existing tests are failing, fix before starting next phase.

4. **Don't burn tokens:** No unnecessary agents or test reruns. Only run tests relevant to new code.
