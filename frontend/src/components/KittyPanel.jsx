/**
 * KittyPanel — declarer sees their 14-card hand and selects exactly 3 to discard.
 *
 * Props:
 *   hand          — array of 14 card objects
 *   declarer      — seat number
 *   trump         — trump suit letter or null
 *   kittyCardIds  — array of card IDs that came from the kitty (for highlighting)
 *   onDiscard     — callback(selectedIds: string[])
 */
import { useState } from 'react'
import CardDisplay from './CardDisplay'

const SEAT_NAMES = ['North', 'East', 'South', 'West']

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
    if (a.id === 'Joker') return 1
    if (b.id === 'Joker') return -1
    const suitA = effectiveSuit(a, trump)
    const suitB = effectiveSuit(b, trump)
    const suitDiff = (SUIT_ORDER[suitA] ?? 9) - (SUIT_ORDER[suitB] ?? 9)
    if (suitDiff !== 0) return suitDiff
    const rankA = isRightBower(a, trump) ? 99 : isLeftBower(a, trump) ? 98 : RANK_ORDER.indexOf(a.rank)
    const rankB = isRightBower(b, trump) ? 99 : isLeftBower(b, trump) ? 98 : RANK_ORDER.indexOf(b.rank)
    return rankB - rankA
  })
}

function KittyPanel({ hand = [], declarer, trump = null, kittyCardIds = [], onDiscard }) {
  const [selected, setSelected] = useState(new Set())

  const kittySet = new Set(kittyCardIds)
  const sorted = sortCards(hand, trump)

  function toggleCard(card) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(card.id)) {
        next.delete(card.id)
      } else if (next.size < 3) {
        next.add(card.id)
      }
      return next
    })
  }

  function handleConfirm() {
    if (selected.size === 3) {
      onDiscard([...selected])
      setSelected(new Set())
    }
  }

  const decName = SEAT_NAMES[declarer] ?? `Seat ${declarer}`

  return (
    <div style={{ border: '1px solid #d1d5db', borderRadius: '6px', padding: '10px', background: '#fefce8' }}>
      <div style={{ fontWeight: 'bold', marginBottom: '4px', color: '#92400e' }}>
        {decName} picks up kitty — select 3 cards to discard
        <span style={{ fontWeight: 'normal', color: '#6b7280', marginLeft: '8px' }}>
          ({selected.size}/3 selected)
        </span>
      </div>

      {kittyCardIds.length > 0 && (
        <div style={{ fontSize: '0.78rem', color: '#92400e', marginBottom: '6px' }}>
          ✨ New from kitty:{' '}
          {kittyCardIds.map(id => <strong key={id} style={{ marginRight: '4px' }}>{id}</strong>)}
        </div>
      )}

      <div style={{ marginBottom: '8px' }}>
        {sorted.map(card => (
          <CardDisplay
            key={card.id}
            card={card}
            selected={selected.has(card.id)}
            // Highlight kitty cards with a gold border
            highlighted={kittySet.has(card.id) && !selected.has(card.id)}
            kittyNew={kittySet.has(card.id)}
            onClick={() => toggleCard(card)}
          />
        ))}
      </div>

      <button
        onClick={handleConfirm}
        disabled={selected.size !== 3}
        style={{
          padding: '6px 16px',
          background: selected.size === 3 ? '#16a34a' : '#d1d5db',
          color: '#fff',
          border: 'none',
          borderRadius: '4px',
          cursor: selected.size === 3 ? 'pointer' : 'not-allowed',
          fontWeight: 'bold',
        }}
      >
        Confirm Discard
      </button>

      {selected.size === 3 && (
        <span style={{ marginLeft: '10px', color: '#6b7280', fontSize: '0.85rem' }}>
          Discarding: {[...selected].join(', ')}
        </span>
      )}
    </div>
  )
}

export default KittyPanel
