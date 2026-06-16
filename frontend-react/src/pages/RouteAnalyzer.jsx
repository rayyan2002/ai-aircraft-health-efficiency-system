import { useState, useEffect } from 'react'
import { getPakFleet, simulate, shortAirline, AIRLINE_ALIAS } from '../api'
import { Page, Card, Label, Badge, Empty, Spinner, C } from '../components/ui'

const AIRPORTS = ['KHI', 'LHE', 'ISB', 'PEW', 'MUX', 'LYP', 'SKT', 'UET', 'GWD', 'DXB', 'DOH', 'JED']
const FILTERS = ['All', 'PIA', 'AirBlue', 'AirSial', 'FlyJinnah']

// Rough age lookup by tail (the simulate endpoint uses age for burn). We pass a
// representative age derived from the fleet list ordering; backend also has real age.
export default function RouteAnalyzer() {
  const [fleet, setFleet]   = useState([])
  const [loading, setLoading] = useState(true)
  const [dep, setDep]       = useState('KHI')
  const [arr, setArr]       = useState('LHE')
  const [filter, setFilter] = useState('All')
  const [results, setResults] = useState([])
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    getPakFleet().then(r => setFleet(r.data.fleet || [])).finally(() => setLoading(false))
  }, [])

  const candidates = fleet.filter(p => filter === 'All' || (AIRLINE_ALIAS[p.airline] || p.airline) === filter)

  const analyze = async () => {
    setRunning(true); setResults([]); setProgress(0)
    const out = []
    for (let i = 0; i < candidates.length; i++) {
      const p = candidates[i]
      try {
        const r = await simulate({ tail_number: p.tail_number, aircraft_age_yrs: 8,
          departure_iata: dep, arrival_iata: arr, weather: 'Clear', cargo_kg: 15000 })
        out.push({
          tail: p.tail_number, airline: AIRLINE_ALIAS[p.airline] || p.airline,
          type: p.aircraft_type, fuel: r.data.predictions.estimated_fuel_litres,
          co2: r.data.predictions.estimated_co2_kg, dist: r.data.predictions.distance_km,
          hours: r.data.predictions.flight_hours,
        })
      } catch { /* skip */ }
      setProgress(Math.round(((i + 1) / candidates.length) * 100))
    }
    out.sort((a, b) => a.fuel - b.fuel)
    setResults(out); setRunning(false)
  }

  if (loading) return <Page title="Route Efficiency Analyzer"><Spinner /></Page>

  const best = results[0]

  return (
    <Page eyebrow="Operations — Fleet Optimization" title="Route Efficiency Analyzer"
      subtitle="Find the most fuel-efficient aircraft to fly a given route">

      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <Label>Departure</Label>
            <select value={dep} onChange={e => setDep(e.target.value)} style={selStyle}>
              {AIRPORTS.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
          <div style={{ fontSize: 20, color: C.dim, paddingBottom: 6 }}>→</div>
          <div>
            <Label>Arrival</Label>
            <select value={arr} onChange={e => setArr(e.target.value)} style={selStyle}>
              {AIRPORTS.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
          <div>
            <Label>Fleet</Label>
            <select value={filter} onChange={e => setFilter(e.target.value)} style={selStyle}>
              {FILTERS.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <button onClick={analyze} disabled={running}
            style={{ padding: '10px 20px', borderRadius: 8, border: 'none', cursor: running ? 'wait' : 'pointer',
                     background: C.accent, color: '#fff', fontSize: 13, fontWeight: 600 }}>
            {running ? `Analyzing ${progress}%` : `Analyze ${candidates.length} Aircraft`}
          </button>
        </div>
      </Card>

      {best && (
        <Card style={{ marginBottom: 16, borderColor: C.green, background: 'rgba(63,185,80,0.04)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
            <div>
              <Label>Recommended — Greenest Option</Label>
              <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 26, fontWeight: 700, color: C.green }}>{best.tail}</div>
              <div style={{ fontSize: 12, color: C.muted }}>{best.airline} · {best.type}</div>
            </div>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 28 }}>
              <Metric label="Distance" value={`${best.dist?.toLocaleString()} km`} />
              <Metric label="Flight Time" value={`${best.hours} h`} />
              <Metric label="Fuel" value={`${best.fuel?.toLocaleString()} L`} color={C.green} />
              <Metric label="CO₂" value={`${best.co2?.toLocaleString()} kg`} color={C.green} />
            </div>
          </div>
        </Card>
      )}

      {results.length > 0 ? (
        <Card style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '50px 1.2fr 1.2fr 1fr 1fr 1fr', padding: '12px 18px', borderBottom: `1px solid ${C.border}`, background: C.hover }}>
            {['#', 'Aircraft', 'Airline', 'Fuel (L)', 'CO₂ (kg)', 'Time (h)'].map(h => (
              <div key={h} style={{ fontSize: 10, fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase', color: C.muted }}>{h}</div>
            ))}
          </div>
          {results.map((r, i) => (
            <div key={r.tail} style={{ display: 'grid', gridTemplateColumns: '50px 1.2fr 1.2fr 1fr 1fr 1fr', padding: '11px 18px', borderBottom: `1px solid ${C.border}`, alignItems: 'center', fontSize: 13, background: i === 0 ? 'rgba(63,185,80,0.05)' : 'transparent' }}>
              <div style={{ color: i === 0 ? C.green : C.dim, fontWeight: 700 }}>{i + 1}</div>
              <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 12, color: C.text }}>{r.tail}</div>
              <div style={{ color: C.muted, fontSize: 12 }}>{r.airline}</div>
              <div style={{ color: i === 0 ? C.green : C.text }}>{r.fuel?.toLocaleString()}</div>
              <div style={{ color: C.text }}>{r.co2?.toLocaleString()}</div>
              <div style={{ color: C.muted }}>{r.hours}</div>
            </div>
          ))}
        </Card>
      ) : !running && <Empty>Select a route and analyze to rank aircraft by fuel efficiency.</Empty>}

      <div style={{ fontSize: 11, color: C.dim, marginTop: 16 }}>
        Rankings use the simulation model (distance, aircraft burn rate, and standard conditions). Lower fuel and CO₂ indicate a greener choice for the route.
      </div>
    </Page>
  )
}

const selStyle = { background: C.card, border: `1px solid ${C.border}`, color: C.text, padding: '8px 14px', borderRadius: 8, fontSize: 13, cursor: 'pointer', minWidth: 120 }
function Metric({ label, value, color }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', letterSpacing: 1 }}>{label}</div>
      <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 16, fontWeight: 700, color: color || C.text, marginTop: 2 }}>{value}</div>
    </div>
  )
}
