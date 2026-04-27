"""
FastAPI routes for the 500 debug webapp.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query

from .schemas import BidRequest, DiscardRequest, PlayRequest, GameStateResponse, EvaluateRequest, EvaluateResponse, TrumpEvalResult
from .game_state import GameState, card_to_dict
from backend.solver.evaluator import evaluate_hand

router = APIRouter()

# One global in-memory game session
_state = GameState()


def _state_response() -> dict:
    return _state.to_response()


# ── Deal ─────────────────────────────────────────────────────────────────────

@router.post("/deal")
def deal_new_hand():
    """Deal a new hand and reset to BIDDING phase."""
    _state.new_deal()
    return _state_response()


# ── State / legal plays ───────────────────────────────────────────────────────

@router.get("/state")
def get_state():
    """Return full current game state."""
    return _state_response()


@router.get("/legal-plays")
def get_legal_plays(seat: int = Query(..., ge=0, le=3)):
    """Return legal card IDs for the given seat."""
    if _state.phase != "PLAYING":
        return {"seat": seat, "legal_plays": []}
    cards = _state.legal_plays_for(seat)
    return {"seat": seat, "legal_plays": [card_to_dict(c) for c in cards]}


# ── Bid ───────────────────────────────────────────────────────────────────────

@router.post("/bid")
def place_bid(req: BidRequest):
    """
    Submit a bid for the given seat.
    bid: "7H" | "8NT" | "NULLO" | "DOUBLE_NULLO" | "PASS"
    """
    try:
        msg = _state.place_bid(req.seat, req.bid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    resp = _state_response()
    resp["message"] = msg  # override with action-specific message
    return resp


# ── Kitty discard ─────────────────────────────────────────────────────────────

@router.post("/discard")
def discard_cards(req: DiscardRequest):
    """
    Declarer discards exactly 3 cards from their 14-card hand.
    card_ids: list of 3 card repr strings (e.g. ["AH", "JC", "Joker"])
    """
    try:
        msg = _state.discard(req.seat, req.card_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    resp = _state_response()
    resp["message"] = msg
    return resp


# ── Play ──────────────────────────────────────────────────────────────────────

# ── Evaluate ─────────────────────────────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_hand_endpoint(req: EvaluateRequest):
    """
    Evaluate the hand for the given seat using the heuristic playout engine.
    Returns expected trick distributions and the optimal bid recommendation.
    Runs ~200 simulated deals × up to 6 trump choices (~1-2s).
    """
    if _state.phase not in ("BIDDING", "KITTY", "PLAYING", "FINISHED"):
        raise HTTPException(status_code=400, detail="No hand dealt yet")
    hand = _state.hands[req.seat]
    if not hand:
        raise HTTPException(status_code=400, detail=f"No cards for seat {req.seat}")

    advice = evaluate_hand(hand, declarer=req.seat, n_samples=req.n_samples)

    return EvaluateResponse(
        optimal_bid=advice.optimal_bid,
        optimal_ev=round(advice.optimal_ev, 1),
        n_samples=advice.n_samples,
        evaluations={
            name: TrumpEvalResult(
                trump_name=name,
                avg_tricks=round(ev.avg_tricks, 2),
                std_dev=round(ev.std_dev, 2),
                histogram=ev.histogram,
                skipped=ev.skipped,
            )
            for name, ev in advice.evaluations.items()
        },
    )


@router.post("/play")
def play_card(req: PlayRequest):
    """
    Play a card for the given seat.
    card_id: repr string of the card (e.g. "AH", "Joker")
    """
    try:
        msg = _state.play_card(req.seat, req.card_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    resp = _state_response()
    resp["message"] = msg
    return resp
