/**
 * CardDisplay — renders a single card as text.
 * "A♠", "J♣", "🃏" for Joker. Red suits in red, black in black.
 */
const SUIT_SYMBOL = { H: '♥', D: '♦', S: '♠', C: '♣', NT: 'NT' }
const RED_SUITS = new Set(['H', 'D'])

function CardDisplay({ card, onClick, highlighted, selected, disabled, kittyNew }) {
  if (!card) return null

  const isJoker = card.id === 'Joker'
  const isRed = !isJoker && RED_SUITS.has(card.suit)

  let label
  if (isJoker) {
    label = '🃏 Joker'
  } else {
    label = `${card.rank}${SUIT_SYMBOL[card.suit] || card.suit}`
  }

  const style = {
    display: 'inline-block',
    padding: '4px 6px',
    margin: '2px',
    border: selected
      ? '2px solid #2563eb'
      : kittyNew
      ? '2px solid #d97706'   // gold for new kitty cards
      : highlighted
      ? '2px solid #16a34a'
      : '1px solid #9ca3af',
    borderRadius: '4px',
    background: selected ? '#dbeafe' : kittyNew ? '#fef3c7' : highlighted ? '#dcfce7' : '#fff',
    color: isRed ? '#dc2626' : '#111',
    fontWeight: highlighted || selected || kittyNew ? 'bold' : 'normal',
    cursor: onClick && !disabled ? 'pointer' : 'default',
    fontSize: '0.9rem',
    fontFamily: 'monospace',
    opacity: disabled ? 0.5 : 1,
    userSelect: 'none',
  }

  return (
    <span
      style={style}
      onClick={!disabled && onClick ? onClick : undefined}
      title={card.id}
    >
      {label}
    </span>
  )
}

export default CardDisplay
