/**
 * EvaluatePanel — shows bid analysis for South's hand.
 *
 * Props:
 *   advice       — response from POST /evaluate (or null)
 *   loading      — boolean, true while request is in flight
 *   onEvaluate   — callback() to trigger evaluation
 *   userBid      — the bid the user actually placed (string or null), for comparison
 */

const SUIT_LABEL = { S: '♠', C: '♣', D: '♦', H: '♥', NT: 'NT', NULLO: 'Nullo' }
const RED_SUITS  = new Set(['H', 'D'])

// Scoring table (mirrors bidding.py)
const BASE_POINTS = {
  6:  { S: 40,  C: 60,  D: 80,  H: 100, NT: 120 },
  7:  { S: 140, C: 160, D: 180, H: 200, NT: 220 },
  8:  { S: 240, C: 260, D: 280, H: 300, NT: 320 },
  9:  { S: 340, C: 360, D: 380, H: 400, NT: 420 },
  10: { S: 440, C: 460, D: 480, H: 500, NT: 520 },
  11: { S: 540, C: 560, D: 580, H: 600, NT: 620 },
}

/** Fraction of samples where declaring side won >= targetTricks */
function pctMaking(histogram, targetTricks) {
  const n = histogram.reduce((a, b) => a + b, 0)
  if (!n) return 0
  return histogram.slice(targetTricks).reduce((a, b) => a + b, 0) / n
}

/** EV for a (level, trump) bid given histogram */
function bidEV(histogram, level, trump) {
  const pts = trump === 'NULLO' ? 250 : (BASE_POINTS[level]?.[trump] ?? 0)
  const p   = trump === 'NULLO' ? pctMaking(histogram, 0) - pctMaking(histogram, 1)
                                : pctMaking(histogram, level)
  // For nullo, p(making) = p(0 tricks) = histogram[0]/n
  const pMake = trump === 'NULLO'
    ? (histogram[0] / (histogram.reduce((a, b) => a + b, 0) || 1))
    : pctMaking(histogram, level)
  return pts * pMake - pts * (1 - pMake)
}

/** Best bid for a single trump (highest EV level) */
function bestBidForTrump(ev, trumpName) {
  if (ev.skipped) return null
  if (trumpName === 'NULLO') {
    const ev_val = bidEV(ev.histogram, 0, 'NULLO')
    return { bid: 'NULLO', ev: ev_val, pts: 250 }
  }
  let best = null
  for (let level = 6; level <= 11; level++) {
    const pts = BASE_POINTS[level][trumpName]
    const ev_val = bidEV(ev.histogram, level, trumpName)
    if (!best || ev_val > best.ev) best = { bid: `${level}${trumpName}`, ev: ev_val, pts }
  }
  return best
}

export default function EvaluatePanel({ advice, loading, onEvaluate, userBid }) {
  const TRUMP_ORDER = ['S', 'C', 'D', 'H', 'NT', 'NULLO']

  return (
    <div style={{
      border: '1px solid #d1d5db', borderRadius: '6px',
      padding: '10px', background: '#f9fafb', marginTop: '8px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
        <span style={{ fontWeight: 'bold', color: '#1d4ed8' }}>Hand Analysis</span>
        <button
          onClick={onEvaluate}
          disabled={loading}
          style={{
            padding: '4px 14px', background: '#2563eb', color: '#fff',
            border: 'none', borderRadius: '4px', cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '0.85rem', opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? 'Analysing…' : advice ? 'Re-analyse' : 'Analyse South\'s Hand'}
        </button>
        {advice && !loading && (
          <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
            {advice.n_samples} samples each
          </span>
        )}
      </div>

      {loading && (
        <div style={{ color: '#6b7280', fontSize: '0.9rem', padding: '8px 0' }}>
          Simulating ~{(200 * 4).toLocaleString()} deals… this takes ~1–2s
        </div>
      )}

      {advice && !loading && (
        <>
          {/* Optimal bid banner */}
          <div style={{
            background: '#dcfce7', border: '1px solid #16a34a',
            borderRadius: '4px', padding: '6px 10px', marginBottom: '8px',
            display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap',
          }}>
            <span style={{ fontWeight: 'bold', color: '#15803d' }}>
              Optimal bid: {advice.optimal_bid}
            </span>
            <span style={{ color: '#15803d', fontSize: '0.9rem' }}>
              EV: {advice.optimal_ev > 0 ? '+' : ''}{advice.optimal_ev.toFixed(0)} pts
            </span>
            {userBid && userBid !== advice.optimal_bid && (
              <span style={{ color: '#b45309', fontSize: '0.9rem' }}>
                You bid: {userBid}
              </span>
            )}
            {userBid && userBid === advice.optimal_bid && (
              <span style={{ color: '#15803d', fontSize: '0.9rem' }}>✓ You got it!</span>
            )}
          </div>

          {/* Per-trump table */}
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.82rem' }}>
            <thead>
              <tr style={{ background: '#f3f4f6' }}>
                <th style={th}>Trump</th>
                <th style={th}>Avg Tricks</th>
                <th style={th}>Best Bid</th>
                <th style={th}>% Making</th>
                <th style={th}>EV</th>
                <th style={th}>Trick distribution (0 → 11)</th>
              </tr>
            </thead>
            <tbody>
              {TRUMP_ORDER.map(trumpName => {
                const ev = advice.evaluations[trumpName]
                if (!ev || ev.skipped) return (
                  <tr key={trumpName} style={{ opacity: 0.4 }}>
                    <td style={{ ...td, fontWeight: 'bold', color: RED_SUITS.has(trumpName) ? '#dc2626' : '#111' }}>
                      {SUIT_LABEL[trumpName]}
                    </td>
                    <td style={td} colSpan={5}>skipped (too few cards)</td>
                  </tr>
                )

                const best = bestBidForTrump(ev, trumpName)
                const isOptimal = best && best.bid === advice.optimal_bid
                const pct = best ? (trumpName === 'NULLO'
                  ? ev.histogram[0] / advice.n_samples
                  : pctMaking(ev.histogram, parseInt(best.bid))) : 0

                return (
                  <tr
                    key={trumpName}
                    style={{ background: isOptimal ? '#f0fdf4' : 'transparent' }}
                  >
                    <td style={{
                      ...td, fontWeight: 'bold',
                      color: RED_SUITS.has(trumpName) ? '#dc2626' : '#111',
                    }}>
                      {SUIT_LABEL[trumpName]}
                      {isOptimal && ' ★'}
                    </td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      {trumpName === 'NULLO'
                        ? `${ev.avg_tricks.toFixed(2)} taken`
                        : ev.avg_tricks.toFixed(2)}
                    </td>
                    <td style={{ ...td, textAlign: 'center', fontWeight: isOptimal ? 'bold' : 'normal' }}>
                      {best ? best.bid : '—'}
                    </td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      {best ? `${(pct * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td style={{
                      ...td, textAlign: 'center',
                      color: best && best.ev >= 0 ? '#15803d' : '#dc2626',
                    }}>
                      {best ? `${best.ev >= 0 ? '+' : ''}${best.ev.toFixed(0)}` : '—'}
                    </td>
                    <td style={{ ...td, minWidth: '160px' }}>
                      <MiniHistogram histogram={ev.histogram} n={advice.n_samples} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {/* Per-level breakdown for the optimal suit */}
          {advice.optimal_bid !== 'NULLO' && (() => {
            const trumpName = advice.optimal_bid.slice(-2).startsWith('N')
              ? 'NT' : advice.optimal_bid.slice(-1)
            const ev = advice.evaluations[trumpName]
            if (!ev || ev.skipped) return null
            return (
              <div style={{ marginTop: '10px' }}>
                <div style={{ fontSize: '0.8rem', color: '#374151', fontWeight: 'bold', marginBottom: '4px' }}>
                  All levels for {SUIT_LABEL[trumpName]}:
                </div>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {[6, 7, 8, 9, 10, 11].map(level => {
                    const pts  = BASE_POINTS[level][trumpName]
                    const p    = pctMaking(ev.histogram, level)
                    const ev_v = bidEV(ev.histogram, level, trumpName)
                    const isOpt = `${level}${trumpName}` === advice.optimal_bid
                    return (
                      <div
                        key={level}
                        style={{
                          padding: '4px 8px', borderRadius: '4px', fontSize: '0.78rem',
                          background: isOpt ? '#dcfce7' : '#f3f4f6',
                          border: `1px solid ${isOpt ? '#16a34a' : '#e5e7eb'}`,
                          fontWeight: isOpt ? 'bold' : 'normal',
                        }}
                      >
                        <div>{level}{SUIT_LABEL[trumpName]} ({pts})</div>
                        <div style={{ color: '#6b7280' }}>{(p * 100).toFixed(0)}% making</div>
                        <div style={{ color: ev_v >= 0 ? '#15803d' : '#dc2626' }}>
                          EV {ev_v >= 0 ? '+' : ''}{ev_v.toFixed(0)}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })()}
        </>
      )}
    </div>
  )
}

/** Tiny bar chart showing trick distribution */
function MiniHistogram({ histogram, n }) {
  const max = Math.max(...histogram, 1)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '1px', height: '24px' }}>
      {histogram.map((count, k) => (
        <div
          key={k}
          title={`${k} tricks: ${count}/${n} (${((count/n)*100).toFixed(0)}%)`}
          style={{
            width: '10px',
            height: `${Math.round((count / max) * 24)}px`,
            background: count === max ? '#2563eb' : '#93c5fd',
            borderRadius: '1px',
            flexShrink: 0,
          }}
        />
      ))}
    </div>
  )
}

const th = {
  border: '1px solid #d1d5db', padding: '4px 8px',
  background: '#f3f4f6', textAlign: 'left', whiteSpace: 'nowrap',
}
const td = {
  border: '1px solid #e5e7eb', padding: '4px 8px', verticalAlign: 'middle',
}
