/**
 * GameLog — shows completed tricks in a simple table.
 *
 * Props:
 *   tricksHistory — array of {cards, seats, winner, declarer_won}
 */
import CardDisplay from './CardDisplay'

const SEAT_NAMES = { 0: 'N', 1: 'E', 2: 'S', 3: 'W' }
const SEAT_FULL = { 0: 'North', 1: 'East', 2: 'South', 3: 'West' }

function GameLog({ tricksHistory = [] }) {
  if (tricksHistory.length === 0) {
    return (
      <div style={{ color: '#9ca3af', fontSize: '0.85rem', marginTop: '8px' }}>
        No tricks played yet.
      </div>
    )
  }

  return (
    <div style={{ marginTop: '8px' }}>
      <div style={{ fontWeight: 'bold', fontSize: '0.85rem', marginBottom: '4px', color: '#374151' }}>
        Completed Tricks ({tricksHistory.length})
      </div>
      <table style={{ borderCollapse: 'collapse', fontSize: '0.8rem', width: '100%' }}>
        <thead>
          <tr style={{ background: '#f3f4f6' }}>
            <th style={th}>#</th>
            <th style={th}>Cards played</th>
            <th style={th}>Winner</th>
            <th style={th}>Side</th>
          </tr>
        </thead>
        <tbody>
          {tricksHistory.map((trick, i) => (
            <tr
              key={i}
              style={{ background: trick.declarer_won ? '#f0fdf4' : '#fef2f2' }}
            >
              <td style={td}>{i + 1}</td>
              <td style={td}>
                {trick.seats.map((seat, j) => (
                  <span key={j} style={{ marginRight: '4px' }}>
                    <span style={{ color: '#6b7280' }}>{SEAT_NAMES[seat]}:</span>
                    <CardDisplay card={trick.cards[j]} />
                  </span>
                ))}
              </td>
              <td style={{ ...td, fontWeight: 'bold' }}>{SEAT_FULL[trick.winner]}</td>
              <td style={{ ...td, color: trick.declarer_won ? '#16a34a' : '#dc2626' }}>
                {trick.declarer_won ? 'Declarer' : 'Opponent'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const th = {
  border: '1px solid #d1d5db',
  padding: '3px 8px',
  textAlign: 'left',
}
const td = {
  border: '1px solid #e5e7eb',
  padding: '3px 8px',
}

export default GameLog
