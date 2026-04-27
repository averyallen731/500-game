"""Pydantic request/response models for the 500 game API."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


# ── Requests ──────────────────────────────────────────────────────────────────

class BidRequest(BaseModel):
    seat: int
    bid: str  # "7H", "NULLO", "DOUBLE_NULLO", "PASS"


class DiscardRequest(BaseModel):
    seat: int
    card_ids: list[str]  # exactly 3 card repr strings, e.g. ["AH", "JC", "Joker"]


class PlayRequest(BaseModel):
    seat: int
    card_id: str  # e.g. "AH", "Joker"


# ── Serialised card ───────────────────────────────────────────────────────────

class CardModel(BaseModel):
    rank: Optional[str]   # "A", "K", ..., "3"; None for Joker
    suit: Optional[str]   # "H", "D", "S", "C", "NT"; None for Joker
    id: str               # repr string used as stable identifier


# ── Top-level state ───────────────────────────────────────────────────────────

class BidHistoryEntry(BaseModel):
    seat: int
    bid: str  # repr of bid or "Pass"


class TrickHistoryEntry(BaseModel):
    cards: list[CardModel]
    seats: list[int]       # parallel to cards — who played each
    winner: int
    declarer_won: bool


class ContractInfo(BaseModel):
    bid: str
    declarer: int
    partner: int
    trump: Optional[str]    # Suit value or None for nullo
    active_seats: list[int]
    tricks_needed: int


# ── Evaluate request / response ───────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    seat: int = 2          # seat whose hand to evaluate (default South)
    n_samples: int = 200   # simulated deals per trump choice


class TrumpEvalResult(BaseModel):
    trump_name: str        # "S" | "C" | "H" | "D" | "NT" | "NULLO"
    avg_tricks: float
    std_dev: float
    histogram: list[int]   # histogram[k] = # samples where declaring side won k tricks
    skipped: bool


class EvaluateResponse(BaseModel):
    optimal_bid: str       # e.g. "8H", "NULLO"
    optimal_ev: float
    n_samples: int
    evaluations: dict[str, TrumpEvalResult]   # keyed by trump_name


class GameStateResponse(BaseModel):
    phase: str                          # IDLE / BIDDING / KITTY / PLAYING / FINISHED
    hands: list[list[CardModel]]        # 4 seats; index=seat number
    kitty: list[CardModel]              # hidden after KITTY phase (empty list)
    bids: list[BidHistoryEntry]
    contract: Optional[ContractInfo]
    current_bidder: Optional[int]
    highest_bid: Optional[str]
    highest_bidder: Optional[int]
    current_leader: Optional[int]
    current_trick: list[dict]           # [{"seat": int, "card": CardModel}]
    tricks_history: list[TrickHistoryEntry]
    declarer_tricks: int
    opponent_tricks: int
    whose_turn: Optional[int]           # seat number for next action
    legal_plays: list[CardModel]        # for whose_turn seat (empty when not PLAYING)
    trick_just_completed: bool          # True when last play finished a trick
    last_trick_winner: Optional[int]    # seat who won the last completed trick
    message: str                        # human-readable status line
