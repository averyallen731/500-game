/**
 * TrickPanel — shows the 4 card slots (N/E/S/W) for the current trick
 * plus a running score line.
 *
 * Props:
 *   currentTrick     — array of {seat, card} objects
 *   declarerTricks   — int
 *   opponentTricks   — int
 *   contract         — contract info object or null
 *   lastTrickWinner  — seat number of last trick winner (or null)
 *   trickJustCompleted — bool
 */
import CardDisplay from './CardDisplay'

const SEAT_NAMES = { 0: 'North', 1: 'East', 2: 'South', 3: 'West' }

function TrickPanel({
  currentTrick = [],
  declarerTricks = 0,
  opponentTricks = 0,
  contract = null,
  lastTrickWinner = null,
  trickJustCompleted = false,
}) {
  // Build a map: seat → card
  const played = {}
  for (const { seat, card } of currentTrick) {
    played[seat] = card
  }

  const activeSeatSet = new Set(contract?.active_seats ?? [0, 1, 2, 3])

  function SlotCard({ seat, position }) {
    const card = played[seat]
    const isWinner = trickJustCompleted && lastTrickWinner === seat
    const inactive = !activeSeatSet.has(seat)

    return (
      <div style={{ textAlign: 'center', width: '80px' }}>
        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '2px' }}>
          {SEAT_NAMES[seat]}
          {inactive && ' (out)'}
        </div>
        <div
          style={{
            minHeight: '36px',
            border: isWinner ? '2px solid #16a34a' : '1px dashed #d1d5db',
            borderRadius: '4px',
            padding: '2px',
            background: isWinner ? '#dcfce7' : inactive ? '#f3f4f6' : '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {card ? (
            <CardDisplay card={card} />
          ) : (
            <span style={{ color: '#d1d5db', fontSize: '0.8rem' }}>—</span>
          )}
        </div>
      </div>
    )
  }

  // Score line
  let declarerLabel = 'Declaring side'
  let opponentLabel = 'Opponents'
  if (contract) {
    const decName = SEAT_NAMES[contract.declarer] ?? 'Declarer'
    const partName = SEAT_NAMES[contract.partner] ?? 'Partner'
    declarerLabel = `${decName}+${partName}`
  }

  const needed = contract?.tricks_needed ?? '?'
  const trump = contract?.trump ?? '—'

  return (
    <div style={{ border: '1px solid #d1d5db', borderRadius: '6px', padding: '10px', background: '#f0fdf4' }}>
      <div style={{ fontWeight: 'bold', fontSize: '0.85rem', marginBottom: '8px', color: '#166534' }}>
        Current Trick
        {contract && (
          <span style={{ fontWeight: 'normal', color: '#6b7280', marginLeft: '8px' }}>
            Contract: {contract.bid} | Trump: {trump} | Need: {needed} | Worth: {contract.point_value ?? '?'} pts
          </span>
        )}
      </div>

      {/* 3×3 grid: N on top, S on bottom, W left, E right, trick cards in center */}
      <div style={{ display: 'grid', gridTemplateColumns: '80px 80px 80px', gridTemplateRows: 'auto auto auto', gap: '4px', marginBottom: '10px', justifyContent: 'center' }}>
        {/* Row 1: North */}
        <div />
        <SlotCard seat={0} />
        <div />
        {/* Row 2: West, center label, East */}
        <SlotCard seat={3} />
        <div style={{ textAlign: 'center', fontSize: '0.7rem', color: '#9ca3af', alignSelf: 'center' }}>
          {currentTrick.length} / {activeSeatSet.size}
        </div>
        <SlotCard seat={1} />
        {/* Row 3: South */}
        <div />
        <SlotCard seat={2} />
        <div />
      </div>

      {/* Score */}
      <div style={{ fontSize: '0.85rem', color: '#374151', display: 'flex', gap: '16px' }}>
        <span>
          <strong>{declarerLabel}:</strong> {declarerTricks}
        </span>
        <span>
          <strong>{opponentLabel}:</strong> {opponentTricks}
        </span>
      </div>

      {trickJustCompleted && lastTrickWinner !== null && (
        <div style={{ marginTop: '4px', color: '#16a34a', fontWeight: 'bold', fontSize: '0.85rem' }}>
          {SEAT_NAMES[lastTrickWinner]} won that trick!
        </div>
      )}
    </div>
  )
}

export default TrickPanel
