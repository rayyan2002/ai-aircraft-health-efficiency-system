import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPakFleet, getFleetHealth, AIRLINE_ALIAS, AIRLINE_COLOR, toIATA } from '../api'
import { Page, Card, Label, Badge, Empty, Spinner, C } from '../components/ui'
import RecomputeButton from '../components/RecomputeButton'

const FILTERS = ['All', 'PIA', 'AirBlue', 'AirSial', 'FlyJinnah']

export default function FleetOverview() {
  const navigate = useNavigate()
  const [fleet,   setFleet]   = useState([])
  const [health,  setHealth]  = useState({})     // tail -> {health, rul, risk}
  const [filter,  setFilter]  = useState('All')
  const [sort,    setSort]    = useState('health')
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [healthReady, setHealthReady] = useState(false)

  // Registry (fast) — refreshed every 30s to keep airborne status live
  useEffect(() => {
    const load = () => getPakFleet()
      .then(r => { setFleet(r.data.fleet || []); setError('') })
      .catch(() => setError('Cannot reach the backend. Is uvicorn running on port 8000?'))
      .finally(() => setLoading(false))
    load()
    const iv = setInterval(load, 30000)
    return () => clearInterval(iv)
  }, [])

  // Turn the fleet_health response into a tail -> {health, rul, risk} map
  const applyHealth = (arr) => {
    const map = {}
    for (const a of arr || []) {
      if (a.health_score != null) {
        map[a.tail_number] = {
          health: a.health_score,
          rul:    a.predicted_rul_cycles,
          risk:   a.risk_level,
        }
      }
    }
    setHealth(map)
    setHealthReady(true)
  }

  // Health for ALL aircraft in ONE call (server-side, cached).
  // Previously this page fired 44 separate requests, each running an LSTM
  // inference — ~30s per page visit. Now it's a single cached request.
  useEffect(() => {
    getFleetHealth()
      .then(r => applyHealth(r.data.fleet))
      .catch(() => setHealthReady(true))   // still show the fleet if health fails
  }, [])

  const hOf = (tail) => health[tail]?.health

  const healthCol = (s) => s == null ? C.border : s >= 70 ? '#3fb950' : s >= 40 ? '#d29922' : '#f85149'
  const riskCol   = (r) => r === 'Low' ? '#3fb950' : r === 'Moderate' ? '#d29922' : '#f85149'

  const scored = Object.values(health).map(v => v.health)
  const stats = {
    total:    fleet.length,
    airborne: fleet.filter(p => p.status === 'airborne').length,
    healthy:  scored.filter(h => h >= 70).length,
    moderate: scored.filter(h => h >= 40 && h < 70).length,
    critical: scored.filter(h => h < 40).length,
  }

  const shown = fleet
    .filter(p => filter === 'All' || (AIRLINE_ALIAS[p.airline] || p.airline) === filter)
    .sort((a, b) => {
      if (sort === 'health') {
        const ha = hOf(a.tail_number), hb = hOf(b.tail_number)
        if (ha == null && hb == null) return 0
        if (ha == null) return 1
        if (hb == null) return -1
        return ha - hb
      }
      if (sort === 'airborne') return (b.status === 'airborne') - (a.status === 'airborne')
      if (sort === 'airline')  return (a.airline || '').localeCompare(b.airline || '')
      return (a.tail_number || '').localeCompare(b.tail_number || '')
    })

  if (loading) return <Page title="Fleet Overview"><Spinner text="Loading fleet..." /></Page>

  if (error) return (
    <Page title="Fleet Overview">
      <Card style={{ borderColor: C.red }}>
        <Empty><span style={{ color: C.red }}>{error}</span></Empty>
      </Card>
    </Page>
  )

  return (
    <Page
      eyebrow="Pakistan Commercial Aviation"
      title="Fleet Overview"
      subtitle="All 44 verified active aircraft"
      right={
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <Badge color={healthReady ? C.green : C.accent}>
            {healthReady ? `${scored.length} analyzed` : 'Analyzing…'}
          </Badge>
          <RecomputeButton onDone={applyHealth} />
        </div>
      }
    >
      {/* KPI strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Total Fleet',   value: stats.total,    color: C.accent },
          { label: 'Airborne',      value: stats.airborne, color: '#3fb950' },
          { label: 'Healthy',       value: healthReady ? stats.healthy  : '··', color: '#3fb950' },
          { label: 'Moderate Risk', value: healthReady ? stats.moderate : '··', color: '#d29922' },
          { label: 'Critical',      value: healthReady ? stats.critical : '··', color: '#f85149' },
        ].map(({ label, value, color }) => (
          <Card key={label} style={{ position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: color }} />
            <Label>{label}</Label>
            <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 28, fontWeight: 700, color }}>
              {value}
            </div>
          </Card>
        ))}
      </div>

      {/* Filters + sort */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)}
            style={{
              padding: '6px 16px', borderRadius: 20, fontSize: 12, cursor: 'pointer',
              border: filter === f ? `1px solid ${C.accent}` : `1px solid ${C.border}`,
              background: filter === f ? 'rgba(56,139,253,0.15)' : 'transparent',
              color: filter === f ? C.accent : C.muted,
            }}>{f}</button>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: C.muted }}>Sort by</span>
          <select value={sort} onChange={e => setSort(e.target.value)}
            disabled={!healthReady && sort === 'health'}
            style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text,
                     padding: '6px 12px', borderRadius: 8, fontSize: 12, cursor: 'pointer' }}>
            <option value="health">Health (worst first)</option>
            <option value="airborne">Airborne first</option>
            <option value="airline">Airline</option>
            <option value="tail">Tail number</option>
          </select>
        </div>
      </div>

      {/* Grid */}
      {shown.length === 0 ? <Empty>No aircraft match this filter.</Empty> : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 12 }}>
          {shown.map(plane => {
            const tail     = plane.tail_number
            const h        = hOf(tail)
            const info     = health[tail]
            const airborne = plane.status === 'airborne'
            const flightNo = plane.current_flight || plane.callsign
            const col      = healthCol(h)
            const airline  = AIRLINE_ALIAS[plane.airline] || plane.airline

            return (
              <div key={tail}
                onClick={() => navigate('/pakistan', { state: { airline, tail } })}
                style={{
                  background: C.card,
                  border: `1px solid ${C.border}`,
                  borderTop: `3px solid ${col}`,      // health colour — never overwritten
                  borderRadius: 12,
                  padding: '16px 18px',
                  cursor: 'pointer',
                  transition: 'box-shadow .15s, transform .15s',
                }}
                // Use box-shadow for hover, NOT borderColor — borderColor would
                // overwrite the coloured top border and erase the health indicator.
                onMouseEnter={e => {
                  e.currentTarget.style.boxShadow = `0 0 0 1px ${C.accent}`
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.boxShadow = 'none'
                  e.currentTarget.style.transform = 'none'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                  <div>
                    <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 15, fontWeight: 700, color: C.text }}>
                      {tail}
                    </div>
                    <div style={{ fontSize: 10, color: C.dim }}>{plane.aircraft_type}</div>
                  </div>
                  <span style={{
                    fontSize: 9, padding: '3px 8px', borderRadius: 20, whiteSpace: 'nowrap',
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    background: airborne ? 'rgba(63,185,80,0.12)' : 'rgba(125,133,144,0.10)',
                    color: airborne ? '#3fb950' : C.muted,
                    border: `1px solid ${airborne ? '#3fb95055' : C.border}`,
                  }}>
                    <span style={{ width: 5, height: 5, borderRadius: '50%',
                                   background: airborne ? '#3fb950' : C.muted,
                                   boxShadow: airborne ? '0 0 5px #3fb950' : 'none' }} />
                    {airborne ? 'AIRBORNE' : 'GROUND'}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 10 }}>
                  <span style={{ fontFamily: 'Orbitron, monospace', fontSize: 30, fontWeight: 700, color: h == null ? C.dim : col }}>
                    {h == null ? '··' : Math.round(h)}
                  </span>
                  <span style={{ fontSize: 11, color: C.dim }}>/ 100</span>
                  {info && (
                    <span style={{ marginLeft: 'auto', fontSize: 10, color: riskCol(info.risk) }}>
                      {info.risk}
                    </span>
                  )}
                </div>

                <div style={{ height: 4, background: C.border, borderRadius: 2, marginTop: 8, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${h ?? 0}%`, background: col,
                                borderRadius: 2, transition: 'width .6s ease' }} />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                              marginTop: 10, paddingTop: 8, borderTop: `1px solid ${C.border}` }}>
                  <span style={{ fontSize: 10, fontFamily: 'Orbitron, monospace',
                                 color: airborne && flightNo ? '#3fb950' : C.dim }}>
                    {airborne && flightNo ? `✈ ${toIATA(flightNo)}` : '—'}
                  </span>
                  <span style={{ fontSize: 10, color: AIRLINE_COLOR[airline] || C.muted }}>
                    {airline}
                  </span>
                </div>

                {info && (
                  <div style={{ fontSize: 10, color: C.dim, marginTop: 5 }}>
                    RUL {info.rul} cycles
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <div style={{ fontSize: 11, color: C.dim, marginTop: 18 }}>
        Health and Remaining Useful Life are predicted per aircraft from its accumulated engine cycles.
        Airborne status and flight numbers come from live ADS-B, matched to each airframe by its ICAO24 hex code.
      </div>
    </Page>
  )
}