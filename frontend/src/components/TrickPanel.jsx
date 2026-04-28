/**
 * TrickPanel — the centre table.  Shows current-trick cards in N/E/S/W
 * positions on a warm felt surface.
 */
import CardDisplay from './CardDisplay'
import { T } from '../theme'

const SEAT_NAMES = { 0: 'North', 1: 'East', 2: 'South', 3: 'West' }

function suitLabel(s) {
  return { S: '♠', C: '♣', H: '♥', D: '♦', NT: 'NT' }[s] ?? s
}

export default function TrickPanel({
  currentTrick = [],
  declarerTricks = 0,
  opponentTricks = 0,
  contract = null,
  lastTrickWinner = null,
  trickJustCompleted = false,
}) {
  const played = {}
  for (const { seat, card } of currentTrick) played[seat] = card

  const activeSeatSet = new Set(contract?.active_seats ?? [0, 1, 2, 3])
  const needed  = contract?.tricks_needed ?? '?'
  const trumpSym = contract?.trump ? suitLabel(contract.trump) : '—'

  // Declaring side label
  let decLabel = 'Declaring'
  if (contract) {
    const d = SEAT_NAMES[contract.declarer]?.[0] ?? '?'
    const p = SEAT_NAMES[contract.partner]?.[0] ?? '?'
    decLabel = `${d}+${p}`
  }

  function Slot({ seat }) {
    const card    = played[seat]
    const winner  = trickJustCompleted && lastTrickWinner === seat
    const inactive = !activeSeatSet.has(seat)

    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '3px',
        width: '62px',
      }}>
        <div style={{
          fontSize: '0.65rem',
          fontFamily: T.font,
          color: winner ? T.winGreen : T.textMuted,
          fontWeight: winner ? '600' : '400',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}>
          {SEAT_NAMES[seat]}{inactive ? ' ·' : ''}
        </div>
        <div style={{
          width: '52px', height: '72px',
          border: winner
            ? `2px solid ${T.winGreen}`
            : `1.5px dashed ${T.panelBorder}`,
          borderRadius: '6px',
          background: winner ? T.winBg : inactive ? 'rgba(0,0,0,0.03)' : 'rgba(255,253,248,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: winner ? `0 0 0 3px rgba(75,105,67,0.15)` : 'none',
          transition: 'all 0.2s',
        }}>
          {card
            ? <CardDisplay card={card} size="lg" />
            : <span style={{ color: T.textFaint, fontSize: '1.1rem' }}>·</span>
          }
        </div>
      </div>
    )
  }

  return (
    <div style={{
      borderRadius: '10px',
      padding: '12px 10px 10px',
      background: T.felt,
      border: `1.5px solid ${T.feltDark}`,
      boxShadow: `inset 0 1px 4px rgba(60,40,20,0.12), 0 2px 6px rgba(60,40,20,0.10)`,
    }}>
      {/* Contract line */}
      {contract && (
        <div style={{
          textAlign: 'center',
          fontFamily: T.font,
          fontSize: '0.72rem',
          color: T.text,
          marginBottom: '10px',
          letterSpacing: '0.02em',
        }}>
          <strong style={{ fontSize: '0.78rem' }}>{contract.bid}</strong>
          <span style={{ color: T.textMuted, margin: '0 5px' }}>·</span>
          <span>{trumpSym}</span>
          <span style={{ color: T.textMuted, margin: '0 5px' }}>·</span>
          <span>need {needed}</span>
          <span style={{ color: T.textMuted, margin: '0 5px' }}>·</span>
          <span style={{ color: T.accent }}>{contract.point_value ?? '?'} pts</span>
        </div>
      )}

      {/* 3×3 compass grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '62px 62px 62px',
        gridTemplateRows: 'auto auto auto',
        gap: '6px',
        justifyContent: 'center',
        marginBottom: '10px',
      }}>
        <div /><Slot seat={0} /><div />
        <Slot seat={3} />
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '0.65rem',
          fontFamily: T.font,
          color: T.textMuted,
          letterSpacing: '0.04em',
        }}>
          {currentTrick.length}/{activeSeatSet.size}
        </div>
        <Slot seat={1} />
        <div /><Slot seat={2} /><div />
      </div>

      {/* Score row */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: '18px',
        fontFamily: T.font,
        fontSize: '0.75rem',
        color: T.text,
        borderTop: `1px solid ${T.feltDark}`,
        paddingTop: '8px',
      }}>
        <span>
          <span style={{ color: T.textMuted }}>{decLabel} </span>
          <strong style={{ fontSize: '0.9rem' }}>{declarerTricks}</strong>
        </span>
        <span style={{ color: T.textMuted }}>vs</span>
        <span>
          <span style={{ color: T.textMuted }}>Opp </span>
          <strong style={{ fontSize: '0.9rem' }}>{opponentTricks}</strong>
        </span>
      </div>

      {trickJustCompleted && lastTrickWinner !== null && (
        <div style={{
          marginTop: '6px',
          textAlign: 'center',
          fontFamily: T.font,
          fontSize: '0.75rem',
          color: T.winGreen,
          fontStyle: 'italic',
        }}>
          {SEAT_NAMES[lastTrickWinner]} takes the trick
        </div>
      )}
    </div>
  )
}
