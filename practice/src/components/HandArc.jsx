/**
 * HandArc — displays a hand of cards in a gentle arc, like holding them.
 * Cards fan out from center with subtle rotation and vertical offset.
 */
import PlayingCard from './PlayingCard'

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

export default function HandArc({ cards = [], trump = null }) {
  const sorted = sortCards(cards, trump)
  const n = sorted.length
  if (n === 0) return null

  const mid = (n - 1) / 2
  // Arc parameters
  const maxAngle = 14       // total spread in degrees (±7° from center)
  const arcDip   = 18       // how many px the edge cards dip below center

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'flex-end',
      gap: '5px',
      paddingTop: `${arcDip + 16}px`,
      paddingBottom: '8px',
    }}>
      {sorted.map((card, i) => {
        const t = n > 1 ? (i - mid) / mid : 0   // −1 … 0 … +1
        const angle = t * (maxAngle / 2)          // degrees
        const dip   = (t * t) * arcDip            // quadratic dip — edges dip, center is highest

        return (
          <div
            key={card.id}
            className="card-hover"
            style={{
              transform: `rotate(${angle}deg) translateY(${dip}px)`,
              transformOrigin: 'center bottom',
              zIndex: i,
            }}
          >
            <PlayingCard card={card} />
          </div>
        )
      })}
    </div>
  )
}
