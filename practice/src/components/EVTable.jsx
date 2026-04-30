/**
 * EVTable — compact EV breakdown table for the result view.
 */
import { T } from '../theme'

const SUIT_SYM   = { S: '♠', C: '♣', D: '♦', H: '♥', NT: 'NT', NULLO: 'Nullo' }
const RED_SUITS  = new Set(['H', 'D'])
const BASE_PTS   = {
  6:  { S: 40,  C: 60,  D: 80,  H: 100, NT: 120 },
  7:  { S: 140, C: 160, D: 180, H: 200, NT: 220 },
  8:  { S: 240, C: 260, D: 280, H: 300, NT: 320 },
  9:  { S: 340, C: 360, D: 380, H: 400, NT: 420 },
  10: { S: 440, C: 460, D: 480, H: 500, NT: 520 },
  11: { S: 540, C: 560, D: 580, H: 600, NT: 620 },
}

function pct(hist, target) {
  const n = hist.reduce((a, b) => a + b, 0)
  return n ? hist.slice(target).reduce((a, b) => a + b, 0) / n : 0
}

function bestBid(ev, trumpName) {
  if (ev.skipped) return null
  if (trumpName === 'NULLO') {
    const n = ev.histogram.reduce((a, b) => a + b, 0) || 1
    const p = ev.histogram[0] / n
    return { bid: 'NULLO', ev: 250 * p - 250 * (1 - p), pct: p }
  }
  let best = null
  for (let level = 6; level <= 11; level++) {
    const pts = BASE_PTS[level][trumpName]
    const p   = pct(ev.histogram, level)
    const val = pts * p - pts * (1 - p)
    if (!best || val > best.ev) best = { bid: `${level}${trumpName}`, ev: val, pct: p }
  }
  return best
}

const ORDER = ['S', 'C', 'D', 'H', 'NT', 'NULLO']

export default function EVTable({ evaluations, optimalBid, n }) {
  const th = {
    padding: '4px 10px',
    fontFamily: T.font,
    fontSize: '0.7rem',
    color: T.textMuted,
    fontWeight: '400',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    borderBottom: `1.5px solid ${T.panelBorder}`,
    textAlign: 'left',
    whiteSpace: 'nowrap',
    background: T.panel,
  }
  const td = {
    padding: '5px 10px',
    fontFamily: T.font,
    fontSize: '0.78rem',
    color: T.text,
    borderBottom: `1px solid rgba(200,181,154,0.3)`,
    verticalAlign: 'middle',
  }

  return (
    <div style={{ overflowX: 'auto', borderRadius: '8px', overflow: 'hidden' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', background: T.card }}>
        <thead>
          <tr>
            <th style={th}>Trump</th>
            <th style={{ ...th, textAlign: 'center' }}>Avg tricks</th>
            <th style={{ ...th, textAlign: 'center' }}>Best bid</th>
            <th style={{ ...th, textAlign: 'center' }}>% making</th>
            <th style={{ ...th, textAlign: 'center' }}>EV</th>
            <th style={th}>Distribution</th>
          </tr>
        </thead>
        <tbody>
          {ORDER.map(name => {
            const ev = evaluations[name]
            if (!ev) return null
            if (ev.skipped) return (
              <tr key={name} style={{ opacity: 0.3 }}>
                <td style={{ ...td, fontWeight: '600', color: RED_SUITS.has(name) ? T.red : T.black, fontSize: '0.88rem' }}>
                  {SUIT_SYM[name]}
                </td>
                <td style={td} colSpan={5}>
                  <em style={{ color: T.textFaint }}>skipped</em>
                </td>
              </tr>
            )

            const best   = bestBid(ev, name)
            const isOpt  = best && best.bid === optimalBid

            return (
              <tr key={name} style={{ background: isOpt ? T.winBg : 'transparent' }}>
                <td style={{
                  ...td, fontWeight: '600',
                  fontSize: '0.9rem',
                  color: RED_SUITS.has(name) ? T.red : T.black,
                }}>
                  {SUIT_SYM[name]}{isOpt && ' ★'}
                </td>
                <td style={{ ...td, textAlign: 'center' }}>
                  {name === 'NULLO' ? `${ev.avg_tricks.toFixed(1)} taken` : ev.avg_tricks.toFixed(1)}
                </td>
                <td style={{ ...td, textAlign: 'center', fontWeight: isOpt ? '600' : '400' }}>
                  {best ? best.bid : '—'}
                </td>
                <td style={{ ...td, textAlign: 'center' }}>
                  {best ? `${(best.pct * 100).toFixed(0)}%` : '—'}
                </td>
                <td style={{
                  ...td, textAlign: 'center', fontWeight: '600',
                  color: best && best.ev >= 0 ? T.winGreen : T.loseBrown,
                }}>
                  {best ? `${best.ev >= 0 ? '+' : ''}${best.ev.toFixed(0)}` : '—'}
                </td>
                <td style={{ ...td }}>
                  <MiniBar histogram={ev.histogram} n={n} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function MiniBar({ histogram, n }) {
  const max = Math.max(...histogram, 1)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '1px', height: '20px' }}>
      {histogram.map((count, k) => (
        <div
          key={k}
          title={`${k} tricks: ${count}/${n}`}
          style={{
            width: '10px',
            height: `${Math.max(2, Math.round((count / max) * 20))}px`,
            background: count === max ? T.accentBorder : T.panelBorder,
            borderRadius: '1px 1px 0 0',
            flexShrink: 0,
          }}
        />
      ))}
    </div>
  )
}
