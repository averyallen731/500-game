/**
 * EvaluatePanel — bid analysis with warm styling.
 */
import { T } from '../theme'

const SUIT_LABEL = { S: '♠', C: '♣', D: '♦', H: '♥', NT: 'NT', NULLO: 'Nullo' }
const RED_SUITS  = new Set(['H', 'D'])

const BASE_POINTS = {
  6:  { S: 40,  C: 60,  D: 80,  H: 100, NT: 120 },
  7:  { S: 140, C: 160, D: 180, H: 200, NT: 220 },
  8:  { S: 240, C: 260, D: 280, H: 300, NT: 320 },
  9:  { S: 340, C: 360, D: 380, H: 400, NT: 420 },
  10: { S: 440, C: 460, D: 480, H: 500, NT: 520 },
  11: { S: 540, C: 560, D: 580, H: 600, NT: 620 },
}

function pctMaking(histogram, targetTricks) {
  const n = histogram.reduce((a, b) => a + b, 0)
  if (!n) return 0
  return histogram.slice(targetTricks).reduce((a, b) => a + b, 0) / n
}

function bidEV(histogram, level, trump) {
  const pts  = trump === 'NULLO' ? 250 : (BASE_POINTS[level]?.[trump] ?? 0)
  const n    = histogram.reduce((a, b) => a + b, 0) || 1
  const pMake = trump === 'NULLO'
    ? histogram[0] / n
    : pctMaking(histogram, level)
  return pts * pMake - pts * (1 - pMake)
}

function bestBidForTrump(ev, trumpName) {
  if (ev.skipped) return null
  if (trumpName === 'NULLO') {
    return { bid: 'NULLO', ev: bidEV(ev.histogram, 0, 'NULLO'), pts: 250 }
  }
  let best = null
  for (let level = 6; level <= 11; level++) {
    const pts   = BASE_POINTS[level][trumpName]
    const ev_val = bidEV(ev.histogram, level, trumpName)
    if (!best || ev_val > best.ev) best = { bid: `${level}${trumpName}`, ev: ev_val, pts }
  }
  return best
}

const TRUMP_ORDER = ['S', 'C', 'D', 'H', 'NT', 'NULLO']

export default function EvaluatePanel({ advice, loading, onEvaluate, userBid }) {
  const th = {
    padding: '5px 10px',
    fontFamily: T.font,
    fontSize: '0.72rem',
    color: T.textMuted,
    fontWeight: '400',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    borderBottom: `2px solid ${T.panelBorder}`,
    background: T.panel,
    textAlign: 'left',
    whiteSpace: 'nowrap',
  }
  const td = {
    padding: '5px 10px',
    borderBottom: `1px solid rgba(200,181,154,0.35)`,
    fontFamily: T.font,
    fontSize: '0.78rem',
    verticalAlign: 'middle',
  }

  return (
    <div style={{
      borderRadius: '8px',
      padding: '12px 14px',
      background: T.panel,
      border: `1px solid ${T.panelBorder}`,
      marginTop: '10px',
    }}>
      {/* Header row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        marginBottom: '10px',
        flexWrap: 'wrap',
      }}>
        <span style={{
          fontFamily: T.font,
          fontWeight: '600',
          fontSize: '0.85rem',
          color: T.text,
        }}>
          Hand Analysis
        </span>
        <button
          onClick={onEvaluate}
          disabled={loading}
          style={{
            padding: '5px 14px',
            fontFamily: T.font,
            fontSize: '0.78rem',
            fontWeight: '600',
            border: `1px solid ${T.accent}`,
            borderRadius: '5px',
            cursor: loading ? 'not-allowed' : 'pointer',
            background: loading ? T.panel : T.accentLight,
            color: T.accent,
            opacity: loading ? 0.6 : 1,
            boxShadow: loading ? 'none' : T.cardShadow,
          }}
        >
          {loading ? 'Analysing…' : advice ? 'Re-analyse' : "Analyse South's Hand"}
        </button>
        {advice && !loading && (
          <span style={{ fontSize: '0.72rem', fontFamily: T.font, color: T.textMuted, fontStyle: 'italic' }}>
            {advice.n_samples} samples
          </span>
        )}
      </div>

      {loading && (
        <div style={{
          color: T.textMuted,
          fontSize: '0.82rem',
          fontFamily: T.font,
          fontStyle: 'italic',
          padding: '6px 0',
        }}>
          Simulating ~{(200 * 4).toLocaleString()} deals…
        </div>
      )}

      {advice && !loading && (
        <>
          {/* Optimal bid banner */}
          <div style={{
            background: T.winBg,
            border: `1px solid ${T.winGreen}`,
            borderRadius: '6px',
            padding: '8px 12px',
            marginBottom: '10px',
            display: 'flex',
            gap: '16px',
            alignItems: 'center',
            flexWrap: 'wrap',
          }}>
            <span style={{ fontFamily: T.font, fontWeight: '600', color: T.winGreen, fontSize: '0.9rem' }}>
              Optimal: {advice.optimal_bid}
            </span>
            <span style={{ fontFamily: T.font, color: T.winGreen, fontSize: '0.82rem' }}>
              EV: {advice.optimal_ev > 0 ? '+' : ''}{advice.optimal_ev.toFixed(0)} pts
            </span>
            {userBid && userBid !== advice.optimal_bid && (
              <span style={{ fontFamily: T.font, color: T.accent, fontSize: '0.82rem', fontStyle: 'italic' }}>
                You bid: {userBid}
              </span>
            )}
            {userBid && userBid === advice.optimal_bid && (
              <span style={{ fontFamily: T.font, color: T.winGreen, fontSize: '0.82rem' }}>
                ✓ Matched
              </span>
            )}
          </div>

          {/* Per-trump table */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%', background: T.cardBg, borderRadius: '6px', overflow: 'hidden' }}>
              <thead>
                <tr>
                  <th style={th}>Trump</th>
                  <th style={{ ...th, textAlign: 'center' }}>Avg Tricks</th>
                  <th style={{ ...th, textAlign: 'center' }}>Best Bid</th>
                  <th style={{ ...th, textAlign: 'center' }}>% Making</th>
                  <th style={{ ...th, textAlign: 'center' }}>EV</th>
                  <th style={th}>Distribution</th>
                </tr>
              </thead>
              <tbody>
                {TRUMP_ORDER.map(trumpName => {
                  const ev = advice.evaluations[trumpName]
                  if (!ev || ev.skipped) return (
                    <tr key={trumpName} style={{ opacity: 0.35 }}>
                      <td style={{ ...td, fontWeight: '600', color: RED_SUITS.has(trumpName) ? T.red : T.black }}>
                        {SUIT_LABEL[trumpName]}
                      </td>
                      <td style={td} colSpan={5}>
                        <span style={{ fontStyle: 'italic', color: T.textMuted }}>skipped — too few cards</span>
                      </td>
                    </tr>
                  )

                  const best      = bestBidForTrump(ev, trumpName)
                  const isOptimal = best && best.bid === advice.optimal_bid
                  const pct       = best
                    ? (trumpName === 'NULLO'
                        ? ev.histogram[0] / advice.n_samples
                        : pctMaking(ev.histogram, parseInt(best.bid)))
                    : 0

                  return (
                    <tr
                      key={trumpName}
                      style={{ background: isOptimal ? T.winBg : 'transparent' }}
                    >
                      <td style={{
                        ...td, fontWeight: '600',
                        color: RED_SUITS.has(trumpName) ? T.red : T.black,
                        fontSize: '0.9rem',
                      }}>
                        {SUIT_LABEL[trumpName]}{isOptimal && ' ★'}
                      </td>
                      <td style={{ ...td, textAlign: 'center' }}>
                        {trumpName === 'NULLO'
                          ? `${ev.avg_tricks.toFixed(2)} taken`
                          : ev.avg_tricks.toFixed(2)}
                      </td>
                      <td style={{ ...td, textAlign: 'center', fontWeight: isOptimal ? '600' : '400' }}>
                        {best ? best.bid : '—'}
                      </td>
                      <td style={{ ...td, textAlign: 'center' }}>
                        {best ? `${(pct * 100).toFixed(0)}%` : '—'}
                      </td>
                      <td style={{
                        ...td, textAlign: 'center', fontWeight: '600',
                        color: best && best.ev >= 0 ? T.winGreen : T.loseBrown,
                      }}>
                        {best ? `${best.ev >= 0 ? '+' : ''}${best.ev.toFixed(0)}` : '—'}
                      </td>
                      <td style={{ ...td, minWidth: '150px' }}>
                        <MiniHistogram histogram={ev.histogram} n={advice.n_samples} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Per-level breakdown for optimal trump */}
          {advice.optimal_bid !== 'NULLO' && (() => {
            const trumpName = advice.optimal_bid.slice(-2).startsWith('N') ? 'NT' : advice.optimal_bid.slice(-1)
            const ev = advice.evaluations[trumpName]
            if (!ev || ev.skipped) return null
            return (
              <div style={{ marginTop: '12px' }}>
                <div style={{ fontFamily: T.font, fontSize: '0.75rem', color: T.textMuted, marginBottom: '6px', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                  All levels — {SUIT_LABEL[trumpName]}
                </div>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {[6, 7, 8, 9, 10, 11].map(level => {
                    const pts   = BASE_POINTS[level][trumpName]
                    const p     = pctMaking(ev.histogram, level)
                    const ev_v  = bidEV(ev.histogram, level, trumpName)
                    const isOpt = `${level}${trumpName}` === advice.optimal_bid
                    return (
                      <div key={level} style={{
                        padding: '6px 10px',
                        borderRadius: '6px',
                        fontFamily: T.font,
                        fontSize: '0.75rem',
                        background: isOpt ? T.winBg : T.cardBg,
                        border: `1px solid ${isOpt ? T.winGreen : T.cardBorder}`,
                        fontWeight: isOpt ? '600' : '400',
                        boxShadow: isOpt ? 'none' : T.cardShadow,
                      }}>
                        <div style={{ color: T.text }}>{level}{SUIT_LABEL[trumpName]} <span style={{ color: T.textMuted, fontWeight: '400' }}>({pts})</span></div>
                        <div style={{ color: T.textMuted, marginTop: '2px' }}>{(p * 100).toFixed(0)}% make</div>
                        <div style={{ color: ev_v >= 0 ? T.winGreen : T.loseBrown, fontWeight: '600' }}>
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

function MiniHistogram({ histogram, n }) {
  const max = Math.max(...histogram, 1)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '1px', height: '22px' }}>
      {histogram.map((count, k) => (
        <div
          key={k}
          title={`${k} tricks: ${count}/${n} (${((count/n)*100).toFixed(0)}%)`}
          style={{
            width: '10px',
            height: `${Math.max(2, Math.round((count / max) * 22))}px`,
            background: count === max ? T.accentMid : T.panelBorder,
            borderRadius: '1px 1px 0 0',
            flexShrink: 0,
            transition: 'height 0.2s',
          }}
        />
      ))}
    </div>
  )
}
