/**
 * Hand — renders a player's hand of cards.
 *
 * Props:
 *   cards           — array of card objects {rank, suit, id}
 *   label           — e.g. "North (0)"
 *   trump           — trump suit letter ("S","C","H","D","NT") or null
 *   selectable      — if true, cards are clickable
 *   selectedCards   — Set of card IDs that are selected
 *   onCardClick     — callback(card)
 *   legalCards      — Set of card IDs that are legal plays (highlighted green)
 *   isCurrentPlayer — bold the label
 *   trickCount      — number of tricks won (shown next to label)
 */
import CardDisplay from './CardDisplay'

// Same-color pairs for bower detection
const SAME_COLOR = { S: 'C', C: 'S', H: 'D', D: 'H' }
const SUIT_ORDER = { S: 0, C: 1, H: 2, D: 3 }
const RANK_ORDER = ['3','4','5','6','7','8','9','10','J','Q','K','A']

function isRightBower(card, trump) {
  return trump && trump !== 'NT' && card.rank === 'J' && card.suit === trump
}

function isLeftBower(card, trump) {
  return trump && trump !== 'NT' && card.rank === 'J' && SAME_COLOR[card.suit] === trump
}

function effectiveSuit(card, trump) {
  if (isRightBower(card, trump) || isLeftBower(card, trump)) return trump
  return card.suit
}

function sortCards(cards, trump) {
  return [...cards].sort((a, b) => {
    // Joker always last
    if (a.id === 'Joker') return 1
    if (b.id === 'Joker') return -1

    const suitA = effectiveSuit(a, trump)
    const suitB = effectiveSuit(b, trump)
    const suitDiff = (SUIT_ORDER[suitA] ?? 9) - (SUIT_ORDER[suitB] ?? 9)
    if (suitDiff !== 0) return suitDiff

    // Within the same suit: right bower > left bower > A > K > ...
    const rankA = isRightBower(a, trump) ? 99 : isLeftBower(a, trump) ? 98 : RANK_ORDER.indexOf(a.rank)
    const rankB = isRightBower(b, trump) ? 99 : isLeftBower(b, trump) ? 98 : RANK_ORDER.indexOf(b.rank)
    return rankB - rankA  // descending
  })
}

function Hand({
  cards = [],
  label = '',
  trump = null,
  selectable = false,
  selectedCards = new Set(),
  onCardClick,
  legalCards = new Set(),
  isCurrentPlayer = false,
  trickCount,
}) {
  const sorted = sortCards(cards, trump)

  const labelStyle = {
    fontWeight: isCurrentPlayer ? 'bold' : 'normal',
    color: isCurrentPlayer ? '#1d4ed8' : '#374151',
    marginBottom: '4px',
    fontSize: '0.85rem',
  }

  return (
    <div style={{ padding: '6px 0' }}>
      <div style={labelStyle}>
        {label}
        {trickCount !== undefined && (
          <span style={{ color: '#6b7280', fontWeight: 'normal', marginLeft: '6px' }}>
            ({trickCount} tricks)
          </span>
        )}
      </div>
      <div>
        {sorted.map((card) => (
          <CardDisplay
            key={card.id}
            card={card}
            highlighted={legalCards.has(card.id)}
            selected={selectedCards.has(card.id)}
            onClick={selectable ? () => onCardClick && onCardClick(card) : undefined}
            disabled={selectable && legalCards.size > 0 && !legalCards.has(card.id)}
          />
        ))}
        {cards.length === 0 && (
          <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>— no cards —</span>
        )}
      </div>
    </div>
  )
}

export default Hand
