/**
 * App.jsx — 500 Debug Webapp
 *
 * Layout:
 *   [Deal button]  Phase indicator  Message
 *   North hand
 *   West hand | TrickPanel | East hand
 *   South hand
 *   BiddingPanel | KittyPanel | GameLog
 */
import { useState, useCallback } from 'react'
import Hand from './components/Hand'
import BiddingPanel from './components/BiddingPanel'
import KittyPanel from './components/KittyPanel'
import TrickPanel from './components/TrickPanel'
import GameLog from './components/GameLog'
import EvaluatePanel from './components/EvaluatePanel'

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

// Simple suit symbol helper used in kitty display
function suitSym(suit) {
  return { H: '♥', D: '♦', S: '♠', C: '♣', NT: 'NT' }[suit] ?? suit
}

function App() {
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [advice, setAdvice] = useState(null)
  const [adviceLoading, setAdviceLoading] = useState(false)
  const [userBid, setUserBid] = useState(null)   // South's bid for comparison

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

  function deal() {
    setAdvice(null)
    setUserBid(null)
    doFetch('/deal', 'POST')
  }
  function refreshState() { doFetch('/state') }

  function bid(bidStr) {
    if (!state) return
    // Record South's bid for later comparison with advice
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
    // After discard, a bot may lead the first trick
    await doFetch('/bot-advance', 'POST')
  }

  function playCard(seat, cardId) {
    doFetch('/play', 'POST', { seat, card_id: cardId })
  }

  // Compute per-seat trick counts (from history)
  function trickCountForSeat(seat) {
    if (!state) return 0
    return state.tricks_history.filter(t => t.winner === seat).length
  }

  // Legal card IDs as a Set
  const legalSet = new Set((state?.legal_plays ?? []).map(c => c.id))
  const whoseTurn = state?.whose_turn
  const phase = state?.phase ?? 'IDLE'

  function handForSeat(seat) {
    return state?.hands?.[seat] ?? []
  }

  function isSelectableForPlaying(seat) {
    return phase === 'PLAYING' && whoseTurn === seat && legalSet.size > 0
  }

  function onCardClickForSeat(seat) {
    return (card) => {
      if (isSelectableForPlaying(seat)) {
        playCard(seat, card.id)
      }
    }
  }

  // Score summary for finished game
  function finishedSummary() {
    if (phase !== 'FINISHED' || !state.contract) return null
    const c = state.contract
    const decName = SEAT_NAMES[c.declarer]
    const made = c.tricks_needed === 0
      ? state.declarer_tricks === 0
      : state.declarer_tricks >= c.tricks_needed
    const decScore = state.declarer_score
    const oppScore = state.opponent_score
    return (
      <div style={{
        padding: '12px', background: made ? '#dcfce7' : '#fee2e2',
        border: `2px solid ${made ? '#16a34a' : '#dc2626'}`,
        borderRadius: '6px', textAlign: 'center',
        marginBottom: '8px',
      }}>
        <div style={{ fontWeight: 'bold', fontSize: '1.05rem', marginBottom: '4px' }}>
          {made
            ? `✅ ${decName} MADE ${c.bid}! (${state.declarer_tricks}/${c.tricks_needed} tricks)`
            : `❌ ${decName} WENT DOWN on ${c.bid}. Got ${state.declarer_tricks}, needed ${c.tricks_needed}.`}
        </div>
        {decScore !== null && oppScore !== null && (
          <div style={{ fontSize: '0.9rem', color: '#374151' }}>
            <strong>Declarer side:</strong>{' '}
            <span style={{ color: decScore >= 0 ? '#16a34a' : '#dc2626' }}>
              {decScore >= 0 ? '+' : ''}{decScore} pts
            </span>
            {'  |  '}
            <strong>Opponents:</strong>{' '}
            <span style={{ color: '#2563eb' }}>+{oppScore} pts</span>
            {oppScore > 0 && (
              <span style={{ color: '#6b7280', fontSize: '0.8rem' }}> ({state.opponent_tricks} tricks × 10)</span>
            )}
          </div>
        )}
      </div>
    )
  }

  // The trump suit from the current contract (letter like "H", "S", or null)
  const trump = state?.contract?.trump ?? null

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', maxWidth: '960px', margin: '0 auto', padding: '12px' }}>
      {/* Header bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '16px',
        marginBottom: '12px', borderBottom: '1px solid #e5e7eb', paddingBottom: '8px',
        flexWrap: 'wrap',
      }}>
        <button
          onClick={deal}
          disabled={loading}
          style={{
            padding: '6px 16px', background: '#2563eb', color: '#fff',
            border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold',
          }}
        >
          Deal New Hand
        </button>
        <span style={{ fontWeight: 'bold', color: '#374151' }}>
          Phase: <span style={{ color: '#1d4ed8' }}>{phase}</span>
        </span>
        {state?.highest_bid && (
          <span style={{ color: '#374151' }}>
            Current bid: <strong>{state.highest_bid}</strong>
            {state.highest_bidder !== null && ` by ${SEAT_NAMES[state.highest_bidder]}`}
          </span>
        )}
        {loading && <span style={{ color: '#9ca3af' }}>loading…</span>}
        <button
          onClick={refreshState}
          disabled={loading}
          style={{ marginLeft: 'auto', padding: '4px 10px', fontSize: '0.8rem', cursor: 'pointer' }}
        >
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: '#fee2e2', border: '1px solid #fca5a5',
          padding: '8px', borderRadius: '4px', marginBottom: '8px', color: '#991b1b',
        }}>
          Error: {error}
        </div>
      )}

      {/* Status message */}
      {state?.message && (
        <div style={{
          background: '#f3f4f6', padding: '6px 10px', borderRadius: '4px',
          marginBottom: '8px', fontSize: '0.9rem', color: '#374151',
        }}>
          {state.message}
        </div>
      )}

      {/* Finished summary */}
      {phase === 'FINISHED' && finishedSummary()}

      {/* Empty state */}
      {!state && (
        <div style={{ textAlign: 'center', color: '#9ca3af', marginTop: '40px', fontSize: '1.1rem' }}>
          Click "Deal New Hand" to start.
        </div>
      )}

      {state && (
        <>
          {/* North hand */}
          <div style={{ textAlign: 'center', marginBottom: '4px' }}>
            <Hand
              cards={handForSeat(0)}
              label="North (0)"
              trump={trump}
              selectable={isSelectableForPlaying(0)}
              onCardClick={onCardClickForSeat(0)}
              legalCards={whoseTurn === 0 ? legalSet : new Set()}
              isCurrentPlayer={whoseTurn === 0}
              trickCount={trickCountForSeat(0)}
            />
          </div>

          {/* Middle row: West | TrickPanel | East */}
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 280px 1fr',
            gap: '8px', alignItems: 'start', marginBottom: '4px',
          }}>
            <Hand
              cards={handForSeat(3)}
              label="West (3)"
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
                label="East (1)"
                trump={trump}
                selectable={isSelectableForPlaying(1)}
                onCardClick={onCardClickForSeat(1)}
                legalCards={whoseTurn === 1 ? legalSet : new Set()}
                isCurrentPlayer={whoseTurn === 1}
                trickCount={trickCountForSeat(1)}
              />
            </div>
          </div>

          {/* South hand */}
          <div style={{ textAlign: 'center', marginBottom: '4px' }}>
            <Hand
              cards={handForSeat(2)}
              label={`South (2)${state.contract?.declarer === 2 ? ' — Declarer' : ''}`}
              trump={trump}
              selectable={isSelectableForPlaying(2)}
              onCardClick={onCardClickForSeat(2)}
              legalCards={whoseTurn === 2 ? legalSet : new Set()}
              isCurrentPlayer={whoseTurn === 2}
              trickCount={trickCountForSeat(2)}
            />
          </div>

          {/* Kitty strip */}
          {phase === 'BIDDING' && (
            <div style={{ marginBottom: '8px', fontSize: '0.85rem', color: '#6b7280' }}>
              <strong>Kitty:</strong>{' '}
              {(state.kitty ?? []).length === 0
                ? '[3 face-down cards]'
                : (state.kitty ?? []).map((c, i) => (
                    <span key={i} style={{ marginRight: '4px' }}>
                      {c.id === 'Joker' ? '🃏' : `${c.rank}${suitSym(c.suit)}`}
                    </span>
                  ))}
            </div>
          )}

          {/* Bottom panels */}
          <div style={{ marginTop: '8px' }}>
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

            {/* Hand analysis — available whenever a hand is dealt */}
            {['BIDDING', 'KITTY', 'PLAYING', 'FINISHED'].includes(phase) && (
              <EvaluatePanel
                advice={advice}
                loading={adviceLoading}
                onEvaluate={evaluateHand}
                userBid={userBid}
              />
            )}
          </div>

          {/* Game log */}
          {(phase === 'PLAYING' || phase === 'FINISHED') && (
            <GameLog tricksHistory={state.tricks_history} />
          )}
        </>
      )}
    </div>
  )
}

export default App
