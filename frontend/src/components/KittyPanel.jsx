/**
 * KittyPanel — declarer picks up the kitty and selects 3 cards to discard.
 */
import { useState } from 'react'
import CardDisplay from './CardDisplay'
import { T } from '../theme'

const SEAT_NAMES = ['North', 'East', 'South', 'West']
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

export default function KittyPanel({ hand = [], declarer, trump = null, kittyCardIds = [], onDiscard }) {
  const [selected, setSelected] = useState(new Set())

  const kittySet = new Set(kittyCardIds)
  const sorted   = sortCards(hand, trump)

  function toggleCard(card) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(card.id)) next.delete(card.id)
      else if (next.size < 3) next.add(card.id)
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
  const ready   = selected.size === 3

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
        marginBottom: '8px',
        display: 'flex',
        alignItems: 'baseline',
        gap: '8px',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontWeight: '600' }}>{decName} picks up the kitty</span>
        <span style={{ color: T.textMuted, fontStyle: 'italic', fontSize: '0.78rem' }}>
          Select 3 cards to discard
        </span>
        <span style={{
          marginLeft: 'auto',
          fontWeight: '600',
          color: ready ? T.winGreen : T.textMuted,
          fontSize: '0.78rem',
        }}>
          {selected.size}/3
        </span>
      </div>

      {kittyCardIds.length > 0 && (
        <div style={{
          fontSize: '0.72rem',
          fontFamily: T.font,
          color: T.gold,
          marginBottom: '8px',
          fontStyle: 'italic',
        }}>
          New from kitty: {kittyCardIds.join(', ')}
        </div>
      )}

      {/* Cards */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '12px' }}>
        {sorted.map(card => (
          <CardDisplay
            key={card.id}
            card={card}
            selected={selected.has(card.id)}
            kittyNew={kittySet.has(card.id) && !selected.has(card.id)}
            highlighted={kittySet.has(card.id) && !selected.has(card.id)}
            onClick={() => toggleCard(card)}
          />
        ))}
      </div>

      {/* Confirm button */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          onClick={handleConfirm}
          disabled={!ready}
          style={{
            padding: '7px 20px',
            fontFamily: T.font,
            fontSize: '0.82rem',
            fontWeight: '600',
            border: `1px solid ${ready ? T.winGreen : T.panelBorder}`,
            borderRadius: '5px',
            cursor: ready ? 'pointer' : 'not-allowed',
            background: ready ? T.winGreen : T.panel,
            color: ready ? '#fff' : T.textMuted,
            boxShadow: ready ? '0 2px 6px rgba(75,105,67,0.25)' : 'none',
            transition: 'all 0.15s',
          }}
        >
          Confirm Discard
        </button>
        {ready && (
          <span style={{ fontSize: '0.75rem', fontFamily: T.font, color: T.textMuted, fontStyle: 'italic' }}>
            Discarding: {[...selected].join(', ')}
          </span>
        )}
      </div>
    </div>
  )
}
