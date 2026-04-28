/**
 * BiddingPanel — bid grid with warm analog styling.
 */
import { T } from '../theme'

const SEAT_NAMES  = ['North', 'East', 'South', 'West']
const SUITS       = ['S', 'C', 'D', 'H', 'NT']
const SUIT_LABELS = { S: '♠ Spades', C: '♣ Clubs', D: '♦ Diamonds', H: '♥ Hearts', NT: 'No Trump' }
const RED_SUITS   = new Set(['H', 'D'])

const BASE_POINTS = {
  6:  { S: 40,  C: 60,  D: 80,  H: 100, NT: 120 },
  7:  { S: 140, C: 160, D: 180, H: 200, NT: 220 },
  8:  { S: 240, C: 260, D: 280, H: 300, NT: 320 },
  9:  { S: 340, C: 360, D: 380, H: 400, NT: 420 },
  10: { S: 440, C: 460, D: 480, H: 500, NT: 520 },
  11: { S: 540, C: 560, D: 580, H: 600, NT: 620 },
}
const NULLO_POINTS        = 250
const DOUBLE_NULLO_POINTS = 500

function bidPoints(bidStr) {
  const norm = bidStr.toUpperCase().replace(/ /g, '_')
  if (norm === 'NULLO')        return NULLO_POINTS
  if (norm === 'DOUBLE_NULLO') return DOUBLE_NULLO_POINTS
  for (const suf of ['NT', 'H', 'D', 'C', 'S']) {
    if (bidStr.endsWith(suf)) {
      const t = parseInt(bidStr.slice(0, -suf.length))
      return BASE_POINTS[t]?.[suf] ?? 0
    }
  }
  return 0
}

export default function BiddingPanel({ currentBidder, highestBid, onBid, bids = [] }) {
  const currentPts         = highestBid ? bidPoints(highestBid) : 0
  const isDoubleNulloCurrent = highestBid === 'Double Nullo'
  const partnerSeat        = (currentBidder + 2) % 4
  const partnerBidNullo    = bids.find(b => b.seat === partnerSeat)?.bid === 'Nullo'

  function canBid(bidStr) {
    const pts = bidPoints(bidStr)
    if (bidStr === 'DOUBLE_NULLO' && !partnerBidNullo) return false
    if (pts > currentPts) return true
    if (pts === currentPts && bidStr === 'DOUBLE_NULLO' && !isDoubleNulloCurrent) return true
    return false
  }

  const seatName = SEAT_NAMES[currentBidder] ?? `Seat ${currentBidder}`

  // Shared cell style
  const thCell = {
    padding: '5px 8px',
    fontFamily: T.font,
    fontSize: '0.75rem',
    color: T.textMuted,
    fontWeight: '400',
    borderBottom: `1px solid ${T.panelBorder}`,
    whiteSpace: 'nowrap',
    textAlign: 'center',
    background: T.panel,
  }
  const tdCell = {
    padding: '3px 4px',
    textAlign: 'center',
    borderBottom: `1px solid rgba(200,181,154,0.3)`,
  }

  return (
    <div style={{
      borderRadius: '8px',
      padding: '12px 14px',
      background: T.panel,
      border: `1px solid ${T.panelBorder}`,
    }}>
      {/* Header */}
      <div style={{
        fontFamily: T.font,
        fontSize: '0.85rem',
        color: T.text,
        marginBottom: '10px',
        display: 'flex',
        alignItems: 'baseline',
        gap: '8px',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontWeight: '600' }}>Bidding</span>
        <span style={{ color: T.textMuted, fontStyle: 'italic' }}>
          {seatName}'s turn
        </span>
        {highestBid && (
          <span style={{ color: T.textMuted, fontSize: '0.78rem' }}>
            · current: <em>{highestBid}</em>
          </span>
        )}
      </div>

      {/* Bid grid */}
      <div style={{ overflowX: 'auto', marginBottom: '10px' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ ...thCell, textAlign: 'left', paddingLeft: '10px' }}>#</th>
              {SUITS.map(s => (
                <th key={s} style={{
                  ...thCell,
                  color: RED_SUITS.has(s) ? T.red : T.black,
                  fontWeight: '600',
                  fontSize: '0.78rem',
                }}>
                  {SUIT_LABELS[s]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[6, 7, 8, 9, 10, 11].map(t => (
              <tr key={t}>
                <td style={{
                  ...tdCell,
                  fontFamily: T.font,
                  fontSize: '0.8rem',
                  color: T.textMuted,
                  paddingLeft: '10px',
                  textAlign: 'left',
                }}>
                  {t}
                </td>
                {SUITS.map(s => {
                  const bidStr = `${t}${s}`
                  const valid  = canBid(bidStr)
                  const isRed  = RED_SUITS.has(s)
                  return (
                    <td key={s} style={tdCell}>
                      <button
                        onClick={() => onBid(bidStr)}
                        disabled={!valid}
                        style={{
                          padding: '4px 6px',
                          fontSize: '0.75rem',
                          fontFamily: T.font,
                          border: `1px solid ${valid ? T.panelBorder : 'transparent'}`,
                          borderRadius: '4px',
                          cursor: valid ? 'pointer' : 'default',
                          background: valid ? T.cardBg : 'transparent',
                          color: valid ? (isRed ? T.red : T.black) : T.textFaint,
                          fontWeight: valid ? '600' : '400',
                          opacity: valid ? 1 : 0.5,
                          boxShadow: valid ? T.cardShadow : 'none',
                          transition: 'all 0.12s',
                          minWidth: '40px',
                        }}
                      >
                        <div>{t}{s === 'NT' ? 'NT' : { S:'♠',C:'♣',D:'♦',H:'♥' }[s]}</div>
                        <div style={{ fontSize: '0.6rem', opacity: 0.65 }}>{bidPoints(bidStr)}</div>
                      </button>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Nullo / Double Nullo / Pass row */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
        {[
          { key: 'NULLO',        label: 'Nullo',        pts: '250' },
          { key: 'DOUBLE_NULLO', label: 'Double Nullo', pts: '500' },
        ].map(({ key, label, pts }) => {
          const valid = canBid(key)
          return (
            <button
              key={key}
              onClick={() => onBid(key)}
              disabled={!valid}
              title={key === 'DOUBLE_NULLO' && !partnerBidNullo ? 'Partner must bid Nullo first' : ''}
              style={{
                padding: '5px 12px',
                fontFamily: T.font,
                fontSize: '0.78rem',
                border: `1px solid ${valid ? T.panelBorder : 'transparent'}`,
                borderRadius: '4px',
                cursor: valid ? 'pointer' : 'default',
                background: valid ? T.cardBg : 'transparent',
                color: valid ? T.black : T.textFaint,
                fontWeight: valid ? '600' : '400',
                opacity: valid ? 1 : 0.5,
                boxShadow: valid ? T.cardShadow : 'none',
              }}
            >
              {label} <span style={{ fontSize: '0.65rem', opacity: 0.7 }}>({pts})</span>
            </button>
          )
        })}
        <button
          onClick={() => onBid('PASS')}
          style={{
            padding: '5px 14px',
            fontFamily: T.font,
            fontSize: '0.78rem',
            border: `1px solid ${T.loseBrown}`,
            borderRadius: '4px',
            cursor: 'pointer',
            background: T.loseBg,
            color: T.loseBrown,
            fontWeight: '600',
            boxShadow: T.cardShadow,
          }}
        >
          Pass
        </button>
      </div>

      {/* Bid history */}
      {bids.length > 0 && (
        <div style={{
          marginTop: '10px',
          fontSize: '0.75rem',
          fontFamily: T.font,
          color: T.textMuted,
          borderTop: `1px solid ${T.panelBorder}`,
          paddingTop: '8px',
        }}>
          {bids.map((b, i) => (
            <span key={i}>
              {SEAT_NAMES[b.seat]}: <em style={{ color: T.text }}>{b.bid}</em>
              {i < bids.length - 1 && <span style={{ margin: '0 6px', color: T.textFaint }}>·</span>}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
