/**
 * BidGrid — clean bid selection for the practice app.
 * All valid bids shown; user clicks one to select, then confirms.
 */
import { T } from '../theme'

const SUITS       = ['S', 'C', 'D', 'H', 'NT']
const SUIT_SYM    = { S: '♠', C: '♣', D: '♦', H: '♥', NT: 'NT' }
const SUIT_LABEL  = { S: 'Spades', C: 'Clubs', D: 'Diamonds', H: 'Hearts', NT: 'No Trump' }
const RED_SUITS   = new Set(['H', 'D'])

const BASE_POINTS = {
  6:  { S: 40,  C: 60,  D: 80,  H: 100, NT: 120 },
  7:  { S: 140, C: 160, D: 180, H: 200, NT: 220 },
  8:  { S: 240, C: 260, D: 280, H: 300, NT: 320 },
  9:  { S: 340, C: 360, D: 380, H: 400, NT: 420 },
  10: { S: 440, C: 460, D: 480, H: 500, NT: 520 },
  11: { S: 540, C: 560, D: 580, H: 600, NT: 620 },
}

function pts(bidStr) {
  const norm = bidStr.toUpperCase().replace(/ /g, '_')
  if (norm === 'NULLO') return 250
  if (norm === 'DOUBLE_NULLO') return 500
  for (const suf of ['NT', 'H', 'D', 'C', 'S']) {
    if (bidStr.endsWith(suf)) {
      const t = parseInt(bidStr.slice(0, -suf.length))
      return BASE_POINTS[t]?.[suf] ?? 0
    }
  }
  return 0
}

export default function BidGrid({ selected, onSelect, highestBid = null }) {
  const currentPts = highestBid ? pts(highestBid) : 0

  function canBid(bidStr) {
    return pts(bidStr) > currentPts
  }

  function BidCell({ bidStr, label, sublabel, isRed = false, wide = false }) {
    const valid   = canBid(bidStr)
    const isSelected = selected === bidStr

    return (
      <button
        onClick={() => valid && onSelect(bidStr)}
        disabled={!valid}
        style={{
          padding: wide ? '8px 16px' : '7px 0',
          width: wide ? 'auto' : '100%',
          fontFamily: T.font,
          fontSize: '0.85rem',
          fontWeight: isSelected ? '600' : '400',
          border: isSelected
            ? `2px solid ${T.selectedBorder}`
            : `1.5px solid ${valid ? T.cardBorder : 'transparent'}`,
          borderRadius: '6px',
          cursor: valid ? 'pointer' : 'default',
          background: isSelected ? T.selectedBg : valid ? T.card : 'transparent',
          color: isSelected
            ? T.selectedBorder
            : valid
              ? (isRed ? T.red : T.black)
              : T.textFaint,
          boxShadow: isSelected
            ? `0 3px 10px rgba(74,114,160,0.25)`
            : valid ? T.cardShadow : 'none',
          opacity: valid ? 1 : 0.4,
          transition: 'all 0.12s',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '1px',
          transform: isSelected ? 'translateY(-2px)' : 'none',
        }}
      >
        <span style={{ fontSize: wide ? '0.88rem' : '0.85rem', lineHeight: 1.2 }}>
          {label}
        </span>
        {sublabel && (
          <span style={{ fontSize: '0.62rem', opacity: 0.65, lineHeight: 1 }}>{sublabel}</span>
        )}
      </button>
    )
  }

  return (
    <div style={{ width: '100%' }}>
      {/* Column headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '28px repeat(5, 1fr)',
        gap: '4px',
        marginBottom: '4px',
      }}>
        <div />
        {SUITS.map(s => (
          <div key={s} style={{
            textAlign: 'center',
            fontFamily: T.font,
            fontSize: '0.72rem',
            color: RED_SUITS.has(s) ? T.red : T.textMuted,
            fontWeight: '600',
            letterSpacing: '0.02em',
          }}>
            {SUIT_SYM[s]}
            <div style={{ fontSize: '0.6rem', fontWeight: '400', color: T.textFaint }}>
              {SUIT_LABEL[s]}
            </div>
          </div>
        ))}
      </div>

      {/* Bid rows */}
      {[6, 7, 8, 9, 10, 11].map(level => (
        <div key={level} style={{
          display: 'grid',
          gridTemplateColumns: '28px repeat(5, 1fr)',
          gap: '4px',
          marginBottom: '4px',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: T.font,
            fontSize: '0.8rem',
            color: T.textMuted,
            fontWeight: '600',
          }}>
            {level}
          </div>
          {SUITS.map(s => (
            <BidCell
              key={s}
              bidStr={`${level}${s}`}
              label={`${level}${SUIT_SYM[s]}`}
              sublabel={`${BASE_POINTS[level][s]}`}
              isRed={RED_SUITS.has(s)}
            />
          ))}
        </div>
      ))}

      {/* Special bids row */}
      <div style={{
        display: 'flex',
        gap: '8px',
        justifyContent: 'center',
        marginTop: '10px',
        paddingTop: '10px',
        borderTop: `1px solid ${T.panelBorder}`,
        flexWrap: 'wrap',
      }}>
        <BidCell bidStr="NULLO"  label="Nullo"        sublabel="250 pts" wide />
        <BidCell bidStr="PASS"   label="Pass"          sublabel=""        wide />
      </div>
    </div>
  )
}
