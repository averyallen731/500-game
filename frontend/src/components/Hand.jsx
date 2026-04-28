/**
 * Hand — renders a player's hand of cards.
 *
 * Props:
 *   cards           — array of card objects {rank, suit, id}
 *   label           — e.g. "North"
 *   trump           — trump suit letter ("S","C","H","D","NT") or null
 *   selectable      — if true, cards are clickable
 *   selectedCards   — Set of card IDs selected
 *   onCardClick     — callback(card)
 *   legalCards      — Set of card IDs that are legal plays
 *   isCurrentPlayer — highlight the label
 *   trickCount      — tricks won (shown next to label)
 */
import CardDisplay from './CardDisplay'
import { T } from '../theme'

const SAME_COLOR  = { S: 'C', C: 'S', H: 'D', D: 'H' }
const SUIT_ORDER  = { S: 0, C: 1, H: 2, D: 3 }
const RANK_ORDER  = ['3','4','5','6','7','8','9','10','J','Q','K','A']

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
    if (a.id === 'Joker') return 1
    if (b.id === 'Joker') return -1
    const sA = effectiveSuit(a, trump), sB = effectiveSuit(b, trump)
    const sd = (SUIT_ORDER[sA] ?? 9) - (SUIT_ORDER[sB] ?? 9)
    if (sd !== 0) return sd
    const rA = isRightBower(a, trump) ? 99 : isLeftBower(a, trump) ? 98 : RANK_ORDER.indexOf(a.rank)
    const rB = isRightBower(b, trump) ? 99 : isLeftBower(b, trump) ? 98 : RANK_ORDER.indexOf(b.rank)
    return rB - rA
  })
}

export default function Hand({
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

  return (
    <div style={{ padding: '4px 0' }}>
      {/* Label row */}
      <div style={{
        fontFamily: T.font,
        fontSize: '0.78rem',
        fontWeight: isCurrentPlayer ? '600' : '400',
        color: isCurrentPlayer ? T.accent : T.textMuted,
        marginBottom: '5px',
        letterSpacing: '0.03em',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
      }}>
        {isCurrentPlayer && (
          <span style={{ color: T.accentMid, fontSize: '0.65rem' }}>▶</span>
        )}
        <span>{label}</span>
        {trickCount !== undefined && (
          <span style={{
            fontWeight: '400',
            color: trickCount > 0 ? T.gold : T.textFaint,
            fontSize: '0.75rem',
          }}>
            · {trickCount} {trickCount === 1 ? 'trick' : 'tricks'}
          </span>
        )}
      </div>

      {/* Cards */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '3px',
        alignItems: 'flex-end',
      }}>
        {sorted.map(card => (
          <CardDisplay
            key={card.id}
            card={card}
            highlighted={legalCards.has(card.id)}
            selected={selectedCards.has(card.id)}
            onClick={selectable ? () => onCardClick?.(card) : undefined}
            disabled={selectable && legalCards.size > 0 && !legalCards.has(card.id)}
          />
        ))}
        {cards.length === 0 && (
          <span style={{
            color: T.textFaint,
            fontSize: '0.82rem',
            fontStyle: 'italic',
            fontFamily: T.font,
            paddingBottom: '4px',
          }}>
            — no cards —
          </span>
        )}
      </div>
    </div>
  )
}
