/**
 * CardDisplay — a proper playing-card shape.
 *
 * Props:
 *   card       — { rank, suit, id }
 *   onClick    — optional click handler
 *   highlighted — legal play (sage green border)
 *   selected   — chosen for discard / action (blue lift)
 *   disabled   — illegal play (faded)
 *   kittyNew   — came from the kitty (gold border)
 *   size       — 'sm' (default, hand) | 'lg' (trick panel)
 */
import { T } from '../theme'

const SUIT_SYMBOL = { H: '♥', D: '♦', S: '♠', C: '♣' }
const RED_SUITS   = new Set(['H', 'D'])

export default function CardDisplay({
  card,
  onClick,
  highlighted,
  selected,
  disabled,
  kittyNew,
  size = 'sm',
}) {
  if (!card) return null

  const isJoker = card.id === 'Joker'
  const isRed   = !isJoker && RED_SUITS.has(card.suit)
  const isLg    = size === 'lg'

  const w    = isLg ? 52 : 42
  const h    = isLg ? 72 : 58
  const rSz  = isLg ? '11px' : '10px'
  const cSz  = isLg ? '22px' : '18px'

  // Border + background state
  let border = `1.5px solid ${T.cardBorder}`
  let bg     = T.cardBg
  let shadow = T.cardShadow
  let lift   = selected ? -6 : 0

  if (selected)   { border = `2px solid ${T.selectedBorder}`; bg = T.selectedBg; shadow = T.cardShadowLifted }
  else if (kittyNew)   { border = `2px solid ${T.kittyBorder}`;  bg = T.kittyBg }
  else if (highlighted){ border = `2px solid ${T.legalBorder}`;  bg = T.legalBg }

  const textColor = isRed ? T.red : T.black

  const outer = {
    position: 'relative',
    display:  'inline-block',
    width:    `${w}px`,
    height:   `${h}px`,
    border,
    borderRadius: '6px',
    background: bg,
    boxShadow: shadow,
    cursor:    onClick && !disabled ? 'pointer' : 'default',
    opacity:   disabled ? 0.38 : 1,
    userSelect: 'none',
    fontFamily: T.font,
    color: textColor,
    flexShrink: 0,
    transform: `translateY(${lift}px)`,
    verticalAlign: 'bottom',
  }

  const cornerTL = {
    position: 'absolute',
    top: '3px', left: '4px',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center',
    lineHeight: 1.1,
    fontWeight: '600',
    fontSize: rSz,
  }

  const cornerBR = {
    ...cornerTL,
    top: 'auto', left: 'auto',
    bottom: '3px', right: '4px',
    transform: 'rotate(180deg)',
  }

  const center = {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: cSz,
    lineHeight: 1,
    pointerEvents: 'none',
  }

  const cls = [
    'card-lift',
    highlighted ? 'card-legal' : '',
  ].filter(Boolean).join(' ')

  const handleClick = (!disabled && onClick) ? onClick : undefined

  if (isJoker) {
    return (
      <div
        style={outer}
        className={cls}
        onClick={handleClick}
        title="Joker"
      >
        <div style={{ ...cornerTL, color: '#7C3AED', fontStyle: 'italic' }}>Jo</div>
        <div style={center}>🃏</div>
        <div style={{ ...cornerBR, color: '#7C3AED', fontStyle: 'italic' }}>Jo</div>
      </div>
    )
  }

  const sym = SUIT_SYMBOL[card.suit] || card.suit

  return (
    <div
      style={outer}
      className={cls}
      onClick={handleClick}
      title={card.id}
    >
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
