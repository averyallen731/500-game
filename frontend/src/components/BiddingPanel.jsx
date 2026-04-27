/**
 * BiddingPanel — bid grid showing all valid bids + Pass.
 *
 * Props:
 *   currentBidder   — seat number whose turn it is (0=N 1=E 2=S 3=W)
 *   highestBid      — repr string of current highest bid (or null)
 *   onBid           — callback(bidStr: string)
 *   bids            — array of {seat, bid} history entries
 */

const SEAT_NAMES = ['North', 'East', 'South', 'West']
const SUITS = ['S', 'C', 'D', 'H', 'NT']
const SUIT_LABELS = { S: '♠ Spades', C: '♣ Clubs', D: '♦ Diamonds', H: '♥ Hearts', NT: 'No Trump' }
const RED_SUITS = new Set(['H', 'D'])

// Point values (mirrors bidding.py)
const SUIT_ORDER_IDX = { S: 0, C: 1, D: 2, H: 3, NT: 4 }
const BASE_POINTS = {
  6:  { S: 40,  C: 60,  D: 80,  H: 100, NT: 120 },
  7:  { S: 140, C: 160, D: 180, H: 200, NT: 220 },
  8:  { S: 240, C: 260, D: 280, H: 300, NT: 320 },
  9:  { S: 340, C: 360, D: 380, H: 400, NT: 420 },
  10: { S: 440, C: 460, D: 480, H: 500, NT: 520 },
  11: { S: 540, C: 560, D: 580, H: 600, NT: 620 },
}
const NULLO_POINTS = 250
const DOUBLE_NULLO_POINTS = 500

function bidPoints(bidStr) {
  // API returns "Nullo" / "Double Nullo"; buttons pass "NULLO" / "DOUBLE_NULLO" — normalise both
  const norm = bidStr.toUpperCase().replace(/ /g, '_')
  if (norm === 'NULLO') return NULLO_POINTS
  if (norm === 'DOUBLE_NULLO') return DOUBLE_NULLO_POINTS
  for (const suf of ['NT', 'H', 'D', 'C', 'S']) {
    if (bidStr.endsWith(suf)) {
      const t = parseInt(bidStr.slice(0, -suf.length))
      return BASE_POINTS[t]?.[suf] ?? 0
    }
  }
  return 0
}

function BiddingPanel({ currentBidder, highestBid, onBid, bids = [] }) {
  const currentPts = highestBid ? bidPoints(highestBid) : 0
  const isDoubleNulloCurrent = highestBid === 'Double Nullo'

  // Has the current bidder's partner already bid Nullo?
  const partnerSeat = (currentBidder + 2) % 4
  const partnerBid = bids.find(b => b.seat === partnerSeat)?.bid ?? null
  const partnerBidNullo = partnerBid === 'Nullo'

  function canBid(bidStr) {
    const pts = bidPoints(bidStr)
    // Double Nullo: partner must have bid Nullo first
    if (bidStr === 'DOUBLE_NULLO' && !partnerBidNullo) return false
    // Must strictly beat the current highest (or equal with Double Nullo overtaking regular)
    if (pts > currentPts) return true
    if (pts === currentPts && bidStr === 'DOUBLE_NULLO' && !isDoubleNulloCurrent) return true
    return false
  }

  const seatName = SEAT_NAMES[currentBidder] ?? `Seat ${currentBidder}`

  return (
    <div style={{ border: '1px solid #d1d5db', borderRadius: '6px', padding: '10px', background: '#f9fafb' }}>
      <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#1d4ed8' }}>
        Bidding — {seatName}'s turn
        {highestBid && <span style={{ fontWeight: 'normal', color: '#374151' }}> (current highest: {highestBid})</span>}
      </div>

      {/* Bid grid */}
      <table style={{ borderCollapse: 'collapse', marginBottom: '8px' }}>
        <thead>
          <tr>
            <th style={thStyle}>Tricks</th>
            {SUITS.map(s => (
              <th key={s} style={{ ...thStyle, color: RED_SUITS.has(s) ? '#dc2626' : '#111' }}>
                {SUIT_LABELS[s]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[6, 7, 8, 9, 10, 11].map(t => (
            <tr key={t}>
              <td style={tdStyle}>{t}</td>
              {SUITS.map(s => {
                const bidStr = `${t}${s}`
                const valid = canBid(bidStr)
                return (
                  <td key={s} style={tdStyle}>
                    <button
                      onClick={() => onBid(bidStr)}
                      disabled={!valid}
                      style={bidBtnStyle(valid, RED_SUITS.has(s))}
                    >
                      <div>{t}{s}</div>
                      <div style={{ fontSize: '0.65rem', opacity: 0.7 }}>{bidPoints(bidStr)}</div>
                    </button>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Nullo / Double Nullo / Pass */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
        <button
          onClick={() => onBid('NULLO')}
          disabled={!canBid('NULLO')}
          style={bidBtnStyle(canBid('NULLO'), false)}
        >
          Nullo (250)
        </button>
        <button
          onClick={() => onBid('DOUBLE_NULLO')}
          disabled={!canBid('DOUBLE_NULLO')}
          title={!partnerBidNullo ? 'Only valid if your partner bid Nullo' : ''}
          style={bidBtnStyle(canBid('DOUBLE_NULLO'), false)}
        >
          Double Nullo (500)
        </button>
        <button
          onClick={() => onBid('PASS')}
          style={{ ...bidBtnStyle(true, false), background: '#fee2e2', borderColor: '#f87171', color: '#991b1b' }}
        >
          Pass
        </button>
      </div>

      {/* Bid history */}
      {bids.length > 0 && (
        <div style={{ marginTop: '10px', fontSize: '0.8rem', color: '#6b7280' }}>
          <strong>Bids so far:</strong>{' '}
          {bids.map((b, i) => (
            <span key={i}>
              {SEAT_NAMES[b.seat]}: <em>{b.bid}</em>
              {i < bids.length - 1 ? ', ' : ''}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

const thStyle = {
  border: '1px solid #d1d5db',
  padding: '4px 8px',
  background: '#f3f4f6',
  fontSize: '0.8rem',
  textAlign: 'center',
}

const tdStyle = {
  border: '1px solid #e5e7eb',
  padding: '2px 4px',
  textAlign: 'center',
}

function bidBtnStyle(enabled, isRed) {
  return {
    padding: '3px 7px',
    fontSize: '0.8rem',
    border: `1px solid ${enabled ? '#9ca3af' : '#e5e7eb'}`,
    borderRadius: '3px',
    cursor: enabled ? 'pointer' : 'not-allowed',
    background: enabled ? '#fff' : '#f3f4f6',
    color: enabled ? (isRed ? '#dc2626' : '#111') : '#d1d5db',
    fontWeight: 'normal',
    opacity: enabled ? 1 : 0.5,
  }
}

export default BiddingPanel
