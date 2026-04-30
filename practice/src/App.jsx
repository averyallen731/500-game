/**
 * Five Hundred — Bidding Practice
 *
 * Flow:
 *   IDLE → deal → auto-pass N/E/W → WAITING (show hand + bid picker)
 *   user picks bid → EVALUATING → RESULT (show comparison + EV table)
 *   "New hand" → back to IDLE
 */
import { useState } from 'react'
import HandArc from './components/HandArc'
import BidGrid from './components/BidGrid'
import EVTable from './components/EVTable'
import { T } from './theme'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

async function call(path, method = 'GET', body = null) {
  const res = await fetch(API_BASE + '/api' + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

const SEAT_NAMES = ['North', 'East', 'South', 'West']
const SUIT_SYM   = { S: '♠', C: '♣', D: '♦', H: '♥', NT: 'NT' }

function formatBid(bid) {
  if (!bid || bid === 'PASS') return 'Pass'
  if (bid === 'NULLO') return 'Nullo'
  if (bid === 'DOUBLE_NULLO') return 'Double Nullo'
  // "8H" → "8♥", "7NT" → "7NT"
  for (const [letter, sym] of Object.entries(SUIT_SYM)) {
    if (bid.endsWith(letter)) {
      return bid.slice(0, -letter.length) + sym
    }
  }
  return bid
}

export default function App() {
  // phase: 'IDLE' | 'DEALING' | 'WAITING' | 'EVALUATING' | 'RESULT'
  const [phase,      setPhase]      = useState('IDLE')
  const [hand,       setHand]       = useState([])
  const [priorBids,  setPriorBids]  = useState([])  // [{seat, bid}]
  const [highestBid, setHighestBid] = useState(null)
  const [myBid,      setMyBid]      = useState(null)   // what user selected
  const [advice,     setAdvice]     = useState(null)
  const [error,      setError]      = useState(null)

  // ── Deal + auto-pass N/E/W ────────────────────────────────────────────────
  async function deal() {
    setPhase('DEALING')
    setError(null)
    setMyBid(null)
    setAdvice(null)
    setPriorBids([])
    setHighestBid(null)

    try {
      let state = await call('/deal', 'POST')

      // Auto-bid PASS for everyone until South's turn
      const bids = []
      while (state.current_bidder !== 2 && state.phase === 'BIDDING') {
        const seat = state.current_bidder
        state = await call('/bid', 'POST', { seat, bid: 'PASS' })
        bids.push({ seat, bid: 'Pass' })
      }

      setHand(state.hands?.[2] ?? [])
      setPriorBids(bids)
      setHighestBid(state.highest_bid ?? null)
      setPhase('WAITING')
    } catch (e) {
      setError(e.message)
      setPhase('IDLE')
    }
  }

  // ── Evaluate after user picks a bid ───────────────────────────────────────
  async function confirmBid(bid) {
    setMyBid(bid)
    setPhase('EVALUATING')
    setError(null)
    try {
      const data = await call('/evaluate', 'POST', { seat: 2, n_samples: 80 })
      setAdvice(data)
      setPhase('RESULT')
    } catch (e) {
      setError(e.message)
      setPhase('WAITING')
    }
  }

  // ─────────────────────────────────────────────────────────────────────────

  const allPassed = priorBids.length > 0 && priorBids.every(b => b.bid === 'Pass')

  function situationText() {
    if (priorBids.length === 0) return 'First to bid'
    if (allPassed) return 'All passed to you — you open'
    const parts = priorBids.map(b => `${SEAT_NAMES[b.seat]}: ${b.bid}`)
    return parts.join('  ·  ')
  }

  // Result comparison
  function resultLabel() {
    if (!advice || !myBid) return null
    const optimal = advice.optimal_bid
    const myDisplay = formatBid(myBid)
    const optDisplay = formatBid(optimal)

    // Compute EV of user's choice
    const myEV   = computeEV(advice, myBid)
    const optEV  = advice.optimal_ev
    const diff   = myEV - optEV
    const evGap  = optEV - myEV   // always ≥ 0; how many EV pts the user gave up

    // Classify mistake: passed, overbid, or underbid (relative to optimal contract size)
    const myPts  = bidPoints(myBid)
    const optPts = bidPoints(optimal)
    let kind = 'wrong-trump'
    if (myBid === 'PASS')          kind = 'passed'
    else if (myPts > optPts)       kind = 'overbid'
    else if (myPts < optPts)       kind = 'underbid'

    const matched = myBid === optimal
    return { matched, myDisplay, optDisplay, myEV, optEV, diff, evGap, kind }
  }

  const res = resultLabel()

  return (
    <div style={{
      minHeight: '100vh',
      background: T.bg,
      fontFamily: T.font,
      color: T.text,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
    }}>
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{
        width: '100%',
        borderBottom: `1px solid ${T.panelBorder}`,
        padding: '14px 24px',
        display: 'flex',
        alignItems: 'baseline',
        gap: '14px',
        background: T.surface,
      }}>
        <span style={{ fontStyle: 'italic', fontWeight: '400', fontSize: '1.15rem', color: T.text }}>
          Five Hundred
        </span>
        <span style={{
          fontSize: '0.72rem',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: T.textMuted,
          borderLeft: `1px solid ${T.panelBorder}`,
          paddingLeft: '14px',
        }}>
          Bidding Practice
        </span>
      </div>

      {/* ── Main content ────────────────────────────────────────────────────── */}
      <div style={{
        width: '100%',
        maxWidth: '860px',
        padding: '32px 24px 48px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '28px',
      }}>

        {/* ── IDLE ──────────────────────────────────────────────────────────── */}
        {phase === 'IDLE' && (
          <div style={{ textAlign: 'center', paddingTop: '80px' }}>
            <DealButton onClick={deal} loading={false} label="Deal a Hand" />
          </div>
        )}

        {/* ── DEALING ───────────────────────────────────────────────────────── */}
        {phase === 'DEALING' && (
          <div style={{ textAlign: 'center', paddingTop: '80px', color: T.textMuted, fontStyle: 'italic' }}>
            Dealing…
          </div>
        )}

        {/* ── WAITING — hand shown, awaiting bid ────────────────────────────── */}
        {(phase === 'WAITING' || phase === 'EVALUATING') && (
          <>
            {/* Hand */}
            <div style={{ width: '100%' }}>
              <HandArc cards={hand} trump={null} />
            </div>

            {/* Divider */}
            <div style={{ width: '100%', borderTop: `1px solid ${T.panelBorder}` }} />

            {/* Bid picker */}
            <div style={{ width: '100%' }}>
              <div style={{
                textAlign: 'center',
                fontFamily: T.font,
                fontSize: '0.88rem',
                color: T.textMuted,
                marginBottom: '16px',
                fontStyle: 'italic',
              }}>
                {phase === 'EVALUATING' ? 'Evaluating…' : 'What would you bid?'}
              </div>
              {phase === 'WAITING' && (
                <BidGrid
                  selected={myBid}
                  onSelect={confirmBid}
                  highestBid={highestBid}
                />
              )}
              {phase === 'EVALUATING' && (
                <div style={{ textAlign: 'center', color: T.textMuted, fontStyle: 'italic', padding: '24px 0' }}>
                  <Spinner />
                  <div style={{ marginTop: '12px', fontSize: '0.82rem' }}>
                    You bid <strong style={{ color: T.text }}>{formatBid(myBid)}</strong> — simulating deals…
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {/* ── RESULT ────────────────────────────────────────────────────────── */}
        {phase === 'RESULT' && advice && res && (
          <>
            {/* Hand (stays visible) */}
            <div style={{ width: '100%' }}>
              <HandArc cards={hand} trump={null} />
            </div>

            {/* Verdict banner */}
            <div style={{
              width: '100%',
              padding: '20px 24px',
              borderRadius: '10px',
              background: res.matched ? T.winBg : T.surface,
              border: `2px solid ${res.matched ? T.winBorder : T.panelBorder}`,
              textAlign: 'center',
            }}>
              {res.matched ? (
                <>
                  <div style={{ fontSize: '1.5rem', marginBottom: '6px' }}>✓</div>
                  <div style={{ fontWeight: '600', fontSize: '1.1rem', color: T.winGreen, marginBottom: '4px' }}>
                    {formatBid(myBid)} — that's the optimal bid
                  </div>
                  <div style={{ fontSize: '0.85rem', color: T.textMuted }}>
                    Expected value: <strong style={{ color: T.winGreen }}>
                      {res.optEV >= 0 ? '+' : ''}{res.optEV.toFixed(0)} pts
                    </strong>
                  </div>
                </>
              ) : (
                <>
                  <div style={{ marginBottom: '10px' }}>
                    <span style={{ fontFamily: T.font, fontSize: '0.78rem', color: T.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      Your bid
                    </span>
                    <div style={{ fontSize: '1.25rem', fontWeight: '600', color: T.text, marginTop: '2px' }}>
                      {res.myDisplay}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: res.myEV >= 0 ? T.winGreen : T.loseBrown }}>
                      EV {res.myEV >= 0 ? '+' : ''}{res.myEV.toFixed(0)} pts
                    </div>
                  </div>

                  <div style={{ fontSize: '1.2rem', color: T.textFaint, marginBottom: '10px' }}>↕</div>

                  <div>
                    <span style={{ fontFamily: T.font, fontSize: '0.78rem', color: T.winGreen, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      Optimal
                    </span>
                    <div style={{ fontSize: '1.25rem', fontWeight: '600', color: T.winGreen, marginTop: '2px' }}>
                      {res.optDisplay}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: T.winGreen }}>
                      EV +{res.optEV.toFixed(0)} pts
                    </div>
                  </div>

                  {res.evGap > 1 && (
                    <div style={{
                      marginTop: '12px',
                      paddingTop: '12px',
                      borderTop: `1px solid ${T.panelBorder}`,
                      fontSize: '0.82rem',
                      color: T.textMuted,
                      fontStyle: 'italic',
                    }}>
                      {(() => {
                        const gap = res.evGap.toFixed(0)
                        switch (res.kind) {
                          case 'passed':
                            return `You passed up ${gap} pts of EV — this hand had a profitable bid`
                          case 'overbid':
                            return `Overbid by ${gap} pts of EV — too aggressive, you'd go set too often`
                          case 'underbid':
                            return `Underbid by ${gap} pts of EV — a higher bid would pay off more`
                          default:
                            return `Wrong trump cost ${gap} pts of EV`
                        }
                      })()}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* EV breakdown */}
            <div style={{ width: '100%' }}>
              <div style={{
                fontFamily: T.font,
                fontSize: '0.75rem',
                color: T.textMuted,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                marginBottom: '8px',
              }}>
                Full hand analysis — {advice.n_samples} samples per trump
              </div>
              <EVTable
                evaluations={advice.evaluations}
                optimalBid={advice.optimal_bid}
                n={advice.n_samples}
              />
            </div>

            {/* New hand button */}
            <DealButton onClick={deal} loading={false} label="New Hand" />
          </>
        )}

        {/* Error */}
        {error && (
          <div style={{
            padding: '10px 16px',
            background: T.loseBg,
            border: `1px solid ${T.loseBrown}`,
            borderRadius: '6px',
            fontSize: '0.82rem',
            color: T.loseBrown,
            fontFamily: T.font,
          }}>
            {error}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const BASE_PTS = {
  6:  { S: 40,  C: 60,  D: 80,  H: 100, NT: 120 },
  7:  { S: 140, C: 160, D: 180, H: 200, NT: 220 },
  8:  { S: 240, C: 260, D: 280, H: 300, NT: 320 },
  9:  { S: 340, C: 360, D: 380, H: 400, NT: 420 },
  10: { S: 440, C: 460, D: 480, H: 500, NT: 520 },
  11: { S: 540, C: 560, D: 580, H: 600, NT: 620 },
}

function bidPoints(bidStr) {
  if (!bidStr || bidStr === 'PASS') return 0
  if (bidStr === 'NULLO') return 250
  if (bidStr === 'DOUBLE_NULLO') return 500
  for (const suf of ['NT', 'H', 'D', 'C', 'S']) {
    if (bidStr.endsWith(suf)) {
      const lvl = parseInt(bidStr.slice(0, -suf.length))
      return BASE_PTS[lvl]?.[suf] ?? 0
    }
  }
  return 0
}

function pctMaking(hist, target) {
  const n = hist.reduce((a, b) => a + b, 0)
  return n ? hist.slice(target).reduce((a, b) => a + b, 0) / n : 0
}

function computeEV(advice, bidStr) {
  if (!bidStr || bidStr === 'PASS') return 0
  if (bidStr === 'NULLO') {
    const ev = advice.evaluations['NULLO']
    if (!ev || ev.skipped) return 0
    const n = ev.histogram.reduce((a, b) => a + b, 0) || 1
    const p = ev.histogram[0] / n
    return 250 * p - 250 * (1 - p)
  }
  // "8H" → level 8, trump H
  for (const suf of ['NT', 'H', 'D', 'C', 'S']) {
    if (bidStr.endsWith(suf)) {
      const level = parseInt(bidStr.slice(0, -suf.length))
      const ev = advice.evaluations[suf]
      if (!ev || ev.skipped) return 0
      const pts = BASE_PTS[level]?.[suf] ?? 0
      const p   = pctMaking(ev.histogram, level)
      return pts * p - pts * (1 - p)
    }
  }
  return 0
}

function DealButton({ onClick, loading, label }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="btn-deal"
      style={{
        padding: '12px 36px',
        fontFamily: T.font,
        fontSize: '0.95rem',
        fontWeight: '600',
        background: T.accent,
        color: '#fff',
        border: 'none',
        borderRadius: '7px',
        cursor: loading ? 'not-allowed' : 'pointer',
        opacity: loading ? 0.7 : 1,
        boxShadow: '0 3px 12px rgba(146,64,14,0.3)',
        letterSpacing: '0.02em',
      }}
    >
      {label}
    </button>
  )
}

function Spinner() {
  return (
    <div style={{
      display: 'inline-block',
      width: '20px',
      height: '20px',
      border: `2px solid ${T.panelBorder}`,
      borderTopColor: T.accent,
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
    }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
