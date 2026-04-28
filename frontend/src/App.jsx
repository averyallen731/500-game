/**
 * App.jsx — Five Hundred
 * Analog / Kitchen Table aesthetic
 */
import { useState, useCallback } from 'react'
import Hand from './components/Hand'
import BiddingPanel from './components/BiddingPanel'
import KittyPanel from './components/KittyPanel'
import TrickPanel from './components/TrickPanel'
import GameLog from './components/GameLog'
import EvaluatePanel from './components/EvaluatePanel'
import { T } from './theme'

const SEAT_NAMES = ['North', 'East', 'South', 'West']
const API = '/api'

async function apiFetch(path, method = 'GET', body = null) {
  const opts = {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  }
  const res = await fetch(API + path, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

function suitSym(suit) {
  return { H: '♥', D: '♦', S: '♠', C: '♣', NT: 'NT' }[suit] ?? suit
}

export default function App() {
  const [state, setState]               = useState(null)
  const [error, setError]               = useState(null)
  const [loading, setLoading]           = useState(false)
  const [advice, setAdvice]             = useState(null)
  const [adviceLoading, setAdviceLoading] = useState(false)
  const [userBid, setUserBid]           = useState(null)

  const doFetch = useCallback(async (path, method = 'GET', body = null) => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiFetch(path, method, body)
      setState(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  function deal() { setAdvice(null); setUserBid(null); doFetch('/deal', 'POST') }
  function refreshState() { doFetch('/state') }

  function bid(bidStr) {
    if (!state) return
    if (state.current_bidder === 2 && bidStr !== 'PASS') setUserBid(bidStr)
    doFetch('/bid', 'POST', { seat: state.current_bidder, bid: bidStr })
  }

  async function evaluateHand() {
    setAdviceLoading(true)
    try {
      const data = await apiFetch('/evaluate', 'POST', { seat: 2, n_samples: 200 })
      setAdvice(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setAdviceLoading(false)
    }
  }

  async function discard(cardIds) {
    if (!state) return
    await doFetch('/discard', 'POST', { seat: state.contract.declarer, card_ids: cardIds })
    await doFetch('/bot-advance', 'POST')
  }

  function playCard(seat, cardId) {
    doFetch('/play', 'POST', { seat, card_id: cardId })
  }

  function trickCountForSeat(seat) {
    if (!state) return 0
    return state.tricks_history.filter(t => t.winner === seat).length
  }

  const legalSet   = new Set((state?.legal_plays ?? []).map(c => c.id))
  const whoseTurn  = state?.whose_turn
  const phase      = state?.phase ?? 'IDLE'
  const trump      = state?.contract?.trump ?? null

  function handForSeat(seat) { return state?.hands?.[seat] ?? [] }

  function isSelectableForPlaying(seat) {
    return phase === 'PLAYING' && whoseTurn === seat && legalSet.size > 0
  }

  function onCardClickForSeat(seat) {
    return (card) => {
      if (isSelectableForPlaying(seat)) playCard(seat, card.id)
    }
  }

  function finishedBanner() {
    if (phase !== 'FINISHED' || !state.contract) return null
    const c    = state.contract
    const made = c.tricks_needed === 0
      ? state.declarer_tricks === 0
      : state.declarer_tricks >= c.tricks_needed
    const decName = SEAT_NAMES[c.declarer]

    return (
      <div style={{
        padding: '12px 16px',
        background: made ? T.winBg : T.loseBg,
        border: `2px solid ${made ? T.winGreen : T.loseBrown}`,
        borderRadius: '8px',
        fontFamily: T.font,
        marginBottom: '10px',
      }}>
        <div style={{
          fontWeight: '600',
          fontSize: '1rem',
          color: made ? T.winGreen : T.loseBrown,
          marginBottom: '4px',
        }}>
          {made
            ? `${decName} made ${c.bid} — ${state.declarer_tricks} of ${c.tricks_needed} tricks`
            : `${decName} went down on ${c.bid} — got ${state.declarer_tricks}, needed ${c.tricks_needed}`}
        </div>
        {state.declarer_score !== null && state.opponent_score !== null && (
          <div style={{ fontSize: '0.82rem', color: T.text }}>
            <span style={{ marginRight: '16px' }}>
              Declaring side:{' '}
              <strong style={{ color: state.declarer_score >= 0 ? T.winGreen : T.loseBrown }}>
                {state.declarer_score >= 0 ? '+' : ''}{state.declarer_score} pts
              </strong>
            </span>
            <span>
              Opponents:{' '}
              <strong style={{ color: T.accent }}>+{state.opponent_score} pts</strong>
              {state.opponent_score > 0 && (
                <span style={{ color: T.textMuted, fontSize: '0.75rem', marginLeft: '4px' }}>
                  ({state.opponent_tricks} tricks × 10)
                </span>
              )}
            </span>
          </div>
        )}
      </div>
    )
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div style={{
      fontFamily: T.font,
      maxWidth: '980px',
      margin: '0 auto',
      padding: '14px 16px',
      minHeight: '100vh',
      background: T.bg,
      color: T.text,
    }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        marginBottom: '14px',
        paddingBottom: '10px',
        borderBottom: `1px solid ${T.panelBorder}`,
        flexWrap: 'wrap',
      }}>
        {/* Title */}
        <span style={{
          fontFamily: T.font,
          fontStyle: 'italic',
          fontWeight: '400',
          fontSize: '1.25rem',
          color: T.text,
          letterSpacing: '0.01em',
          marginRight: '4px',
        }}>
          Five Hundred
        </span>

        {/* Deal button */}
        <button
          onClick={deal}
          disabled={loading}
          style={{
            padding: '6px 18px',
            fontFamily: T.font,
            fontSize: '0.82rem',
            fontWeight: '600',
            background: T.accent,
            color: '#fff',
            border: 'none',
            borderRadius: '5px',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.7 : 1,
            boxShadow: '0 2px 6px rgba(146,64,14,0.3)',
            letterSpacing: '0.02em',
          }}
        >
          Deal
        </button>

        {/* Phase pill */}
        <span style={{
          padding: '3px 10px',
          borderRadius: '20px',
          fontSize: '0.72rem',
          fontFamily: T.font,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          background: T.panel,
          color: T.textMuted,
          border: `1px solid ${T.panelBorder}`,
        }}>
          {phase}
        </span>

        {state?.highest_bid && (
          <span style={{ fontFamily: T.font, fontSize: '0.82rem', color: T.text }}>
            <span style={{ color: T.textMuted }}>Bid: </span>
            <strong>{state.highest_bid}</strong>
            {state.highest_bidder !== null && (
              <span style={{ color: T.textMuted }}> · {SEAT_NAMES[state.highest_bidder]}</span>
            )}
          </span>
        )}

        {loading && (
          <span style={{ color: T.textMuted, fontSize: '0.78rem', fontStyle: 'italic' }}>…</span>
        )}

        <button
          onClick={refreshState}
          disabled={loading}
          style={{
            marginLeft: 'auto',
            padding: '4px 10px',
            fontFamily: T.font,
            fontSize: '0.72rem',
            cursor: 'pointer',
            background: 'transparent',
            border: `1px solid ${T.panelBorder}`,
            borderRadius: '4px',
            color: T.textMuted,
          }}
        >
          Refresh
        </button>
      </div>

      {/* ── Error ──────────────────────────────────────────────────────────── */}
      {error && (
        <div style={{
          background: T.loseBg,
          border: `1px solid ${T.loseBrown}`,
          padding: '8px 12px',
          borderRadius: '6px',
          marginBottom: '10px',
          fontFamily: T.font,
          fontSize: '0.82rem',
          color: T.loseBrown,
        }}>
          {error}
        </div>
      )}

      {/* ── Status message ─────────────────────────────────────────────────── */}
      {state?.message && (
        <div style={{
          background: T.panel,
          padding: '6px 12px',
          borderRadius: '5px',
          marginBottom: '10px',
          fontFamily: T.font,
          fontSize: '0.82rem',
          color: T.textMuted,
          fontStyle: 'italic',
          border: `1px solid ${T.panelBorder}`,
        }}>
          {state.message}
        </div>
      )}

      {/* ── Finished banner ────────────────────────────────────────────────── */}
      {phase === 'FINISHED' && finishedBanner()}

      {/* ── Empty state ────────────────────────────────────────────────────── */}
      {!state && (
        <div style={{
          textAlign: 'center',
          color: T.textFaint,
          marginTop: '60px',
          fontSize: '1rem',
          fontFamily: T.font,
          fontStyle: 'italic',
        }}>
          Press Deal to start a hand.
        </div>
      )}

      {/* ── Game layout ────────────────────────────────────────────────────── */}
      {state && (
        <>
          {/* North */}
          <div style={{ textAlign: 'center', marginBottom: '6px' }}>
            <Hand
              cards={handForSeat(0)}
              label={`North${state.contract?.declarer === 0 ? ' — Declarer' : ''}`}
              trump={trump}
              selectable={isSelectableForPlaying(0)}
              onCardClick={onCardClickForSeat(0)}
              legalCards={whoseTurn === 0 ? legalSet : new Set()}
              isCurrentPlayer={whoseTurn === 0}
              trickCount={trickCountForSeat(0)}
            />
          </div>

          {/* Middle row: West | Table | East */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 296px 1fr',
            gap: '10px',
            alignItems: 'start',
            marginBottom: '6px',
          }}>
            <Hand
              cards={handForSeat(3)}
              label={`West${state.contract?.declarer === 3 ? ' — Declarer' : ''}`}
              trump={trump}
              selectable={isSelectableForPlaying(3)}
              onCardClick={onCardClickForSeat(3)}
              legalCards={whoseTurn === 3 ? legalSet : new Set()}
              isCurrentPlayer={whoseTurn === 3}
              trickCount={trickCountForSeat(3)}
            />
            <TrickPanel
              currentTrick={state.current_trick}
              declarerTricks={state.declarer_tricks}
              opponentTricks={state.opponent_tricks}
              contract={state.contract}
              lastTrickWinner={state.last_trick_winner}
              trickJustCompleted={state.trick_just_completed}
            />
            <div style={{ textAlign: 'right' }}>
              <Hand
                cards={handForSeat(1)}
                label={`East${state.contract?.declarer === 1 ? ' — Declarer' : ''}`}
                trump={trump}
                selectable={isSelectableForPlaying(1)}
                onCardClick={onCardClickForSeat(1)}
                legalCards={whoseTurn === 1 ? legalSet : new Set()}
                isCurrentPlayer={whoseTurn === 1}
                trickCount={trickCountForSeat(1)}
              />
            </div>
          </div>

          {/* South */}
          <div style={{ textAlign: 'center', marginBottom: '6px' }}>
            <Hand
              cards={handForSeat(2)}
              label={`South${state.contract?.declarer === 2 ? ' — Declarer' : ''}`}
              trump={trump}
              selectable={isSelectableForPlaying(2)}
              onCardClick={onCardClickForSeat(2)}
              legalCards={whoseTurn === 2 ? legalSet : new Set()}
              isCurrentPlayer={whoseTurn === 2}
              trickCount={trickCountForSeat(2)}
            />
          </div>

          {/* Kitty strip (bidding phase) */}
          {phase === 'BIDDING' && (
            <div style={{
              marginBottom: '10px',
              fontSize: '0.78rem',
              fontFamily: T.font,
              color: T.textMuted,
              fontStyle: 'italic',
            }}>
              Kitty:{' '}
              {(state.kitty ?? []).length === 0
                ? '[3 face-down cards]'
                : (state.kitty ?? []).map((c, i) => (
                    <span key={i} style={{ marginRight: '6px', color: T.text }}>
                      {c.id === 'Joker' ? '🃏' : `${c.rank}${suitSym(c.suit)}`}
                    </span>
                  ))
              }
            </div>
          )}

          {/* ── Bottom panels ───────────────────────────────────────────────── */}
          <div style={{ marginTop: '10px' }}>
            {phase === 'BIDDING' && (
              <BiddingPanel
                currentBidder={state.current_bidder}
                highestBid={state.highest_bid}
                onBid={bid}
                bids={state.bids}
              />
            )}

            {phase === 'KITTY' && state.contract && (
              <KittyPanel
                hand={handForSeat(state.contract.declarer)}
                declarer={state.contract.declarer}
                trump={trump}
                kittyCardIds={state.kitty_card_ids ?? []}
                onDiscard={discard}
              />
            )}

            {['BIDDING', 'KITTY', 'PLAYING', 'FINISHED'].includes(phase) && (
              <EvaluatePanel
                advice={advice}
                loading={adviceLoading}
                onEvaluate={evaluateHand}
                userBid={userBid}
              />
            )}
          </div>

          {/* ── Game log ─────────────────────────────────────────────────────── */}
          {(phase === 'PLAYING' || phase === 'FINISHED') && (
            <GameLog tricksHistory={state.tricks_history} />
          )}
        </>
      )}
    </div>
  )
}
