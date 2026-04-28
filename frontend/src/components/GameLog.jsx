/**
 * GameLog — completed tricks in a warm table.
 */
import CardDisplay from './CardDisplay'
import { T } from '../theme'

const SEAT_NAMES = { 0: 'N', 1: 'E', 2: 'S', 3: 'W' }
const SEAT_FULL  = { 0: 'North', 1: 'East', 2: 'South', 3: 'West' }

export default function GameLog({ tricksHistory = [] }) {
  if (tricksHistory.length === 0) return (
    <div style={{
      color: T.textFaint,
      fontSize: '0.82rem',
      fontFamily: T.font,
      fontStyle: 'italic',
      marginTop: '10px',
    }}>
      No tricks played yet.
    </div>
  )

  const th = {
    padding: '5px 10px',
    fontFamily: T.font,
    fontSize: '0.72rem',
    color: T.textMuted,
    fontWeight: '400',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    borderBottom: `2px solid ${T.panelBorder}`,
    background: T.panel,
    textAlign: 'left',
    whiteSpace: 'nowrap',
  }
  const td = {
    padding: '5px 10px',
    borderBottom: `1px solid rgba(200,181,154,0.35)`,
    fontFamily: T.font,
    fontSize: '0.78rem',
    verticalAlign: 'middle',
  }

  return (
    <div style={{ marginTop: '12px' }}>
      <div style={{
        fontFamily: T.font,
        fontSize: '0.78rem',
        fontWeight: '600',
        color: T.text,
        marginBottom: '6px',
        letterSpacing: '0.02em',
      }}>
        Trick History ({tricksHistory.length} of 11)
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', background: T.cardBg, borderRadius: '6px', overflow: 'hidden' }}>
          <thead>
            <tr>
              <th style={th}>#</th>
              <th style={th}>Cards</th>
              <th style={th}>Winner</th>
              <th style={th}>Side</th>
            </tr>
          </thead>
          <tbody>
            {tricksHistory.map((trick, i) => (
              <tr
                key={i}
                style={{ background: trick.declarer_won ? T.winBg : T.loseBg }}
              >
                <td style={{ ...td, color: T.textMuted, width: '28px' }}>{i + 1}</td>
                <td style={td}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', alignItems: 'center' }}>
                    {trick.seats.map((seat, j) => (
                      <span key={j} style={{ display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                        <span style={{ fontSize: '0.65rem', color: T.textMuted }}>{SEAT_NAMES[seat]}</span>
                        <CardDisplay card={trick.cards[j]} />
                      </span>
                    ))}
                  </div>
                </td>
                <td style={{ ...td, fontWeight: '600', color: T.text }}>{SEAT_FULL[trick.winner]}</td>
                <td style={{ ...td, color: trick.declarer_won ? T.winGreen : T.loseBrown, fontWeight: '600' }}>
                  {trick.declarer_won ? 'Declarer' : 'Opp.'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
