/**
 * PlayingCard — a full playing-card shape for the practice app.
 * Larger than the debug app (52×74px default, 60×84px for 'lg').
 */
import { T } from '../theme'

const SYM  = { H: '♥', D: '♦', S: '♠', C: '♣' }
const RED  = new Set(['H', 'D'])

export default function PlayingCard({ card, size = 'md', selected, faceDown }) {
  if (!card) return null

  const isLg    = size === 'lg'
  const w       = isLg ? 60 : 52
  const h       = isLg ? 84 : 74
  const rSz     = isLg ? '12px' : '11px'
  const cSz     = isLg ? '26px' : '22px'
  const isJoker = card.id === 'Joker'
  const isRed   = !isJoker && RED.has(card.suit)

  const border = selected
    ? `2px solid ${T.selectedBorder}`
    : `1.5px solid ${T.cardBorder}`
  const bg = selected ? T.selectedBg : T.card
  const shadow = selected ? `0 6px 16px rgba(74,114,160,0.3), 0 2px 5px rgba(60,40,20,0.12)` : T.cardShadow

  const outer = {
    display: 'inline-block',
    position: 'relative',
    width: `${w}px`,
    height: `${h}px`,
    border,
    borderRadius: '7px',
    background: faceDown ? T.surface : bg,
    boxShadow: shadow,
    userSelect: 'none',
    fontFamily: T.font,
    color: isRed ? T.red : T.black,
    flexShrink: 0,
    transform: selected ? 'translateY(-8px)' : undefined,
    transition: 'transform 0.15s, box-shadow 0.15s',
  }

  if (faceDown) {
    return (
      <div style={{
        ...outer,
        background: `repeating-linear-gradient(
          45deg,
          ${T.surface},
          ${T.surface} 4px,
          ${T.panelBorder} 4px,
          ${T.panelBorder} 5px
        )`,
      }} />
    )
  }

  const cornerTL = {
    position: 'absolute', top: '4px', left: '5px',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', lineHeight: 1.1,
    fontWeight: '600', fontSize: rSz,
  }
  const cornerBR = {
    ...cornerTL,
    top: 'auto', left: 'auto',
    bottom: '4px', right: '5px',
    transform: 'rotate(180deg)',
  }
  const center = {
    position: 'absolute', inset: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: cSz, lineHeight: 1, pointerEvents: 'none',
  }

  if (isJoker) {
    return (
      <div style={outer} title="Joker">
        <div style={{ ...cornerTL, color: '#7C3AED', fontStyle: 'italic', fontSize: '10px' }}>Jo</div>
        <div style={center}>🃏</div>
        <div style={{ ...cornerBR, color: '#7C3AED', fontStyle: 'italic', fontSize: '10px' }}>Jo</div>
      </div>
    )
  }

  const sym = SYM[card.suit] || card.suit

  return (
    <div style={outer} title={card.id}>
      <div style={cornerTL}>
        <span>{card.rank}</span>
        <span style={{ fontSize: `${parseInt(rSz) - 1}px` }}>{sym}</span>
      </div>
      <div style={center}>{sym}</div>
      <div style={cornerBR}>
        <span>{card.rank}</span>
        <span style={{ fontSize: `${parseInt(rSz) - 1}px` }}>{sym}</span>
      </div>
    </div>
  )
}
