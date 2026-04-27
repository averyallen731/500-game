# Double Dummy Solver — How It Works

## The Core Idea

A "double dummy" solver assumes all cards are face-up — every player can see every hand. This sounds unrealistic, but it's the right tool for a **bidding evaluator** because:

> We sample 200+ random deals consistent with your visible hand, solve each one optimally, then average the results. The averaging step is what models uncertainty. Each individual solve can assume perfect information.

This is mathematically sound: the average of 200 perfect-information results approximates your real expected trick count across the distribution of possible deals.

## The Algorithm: Minimax + Alpha-Beta Pruning

500 is a two-team game: declarers (you + partner) vs. defenders. At every trick, the current player picks a card. We model this as a game tree:

- **Maximizing nodes:** declarer-side player to move — pick the card that wins the most tricks
- **Minimizing nodes:** defender-side player to move — pick the card that concedes the fewest tricks

**Alpha-beta pruning** cuts branches we know won't affect the result. If the maximizer has already found a path winning 8 tricks, and the minimizer is currently on a path that can hold them to 7, we stop searching that branch. In practice this eliminates the majority of the game tree.

**Transposition table** (memoization): many different sequences of plays reach the same game state (same remaining cards, same tricks won, same lead). We cache results by hashing the state — a frozenset of each player's remaining cards + current trick context. This is the biggest performance win.

## Handling Nullo

Nullo (and double nullo) just inverts the objective: the declarer side tries to **minimize** tricks won, and we flip maximizing/minimizing. The same minimax code handles it with a sign change.

## Why Not Pure Rule-Based?

Rule-based AI needs explicit logic for every situation: when to finesse, when to lead partner's void suit (short-suiting setup), endplay timing. This is brittle and misses edge cases. Minimax discovers the optimal play for all these situations automatically — if leading a suit sets up partner's trump, the search finds it because that path wins more tricks.

## Future: ISMCTS (v2)

In real play, bots can't see each other's cards. Information Set Monte Carlo Tree Search (ISMCTS) handles this by:
1. Sampling possible worlds consistent with what the bot has observed (suits others have voided, cards played)
2. Running the double dummy solver on each sampled world
3. Choosing the move that performs best on average across samples

DD is a subroutine of ISMCTS — so everything built in v1 carries forward.
