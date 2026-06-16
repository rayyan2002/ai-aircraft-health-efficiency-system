import { useState, useEffect } from 'react'
import { getPakFleet, simulate, shortAirline, AIRLINE_ALIAS } from '../api'
import { Page, Card, Label, Kpi, Badge, Empty, Spinner, C } from '../components/ui'

const AIRPORTS = ['KHI', 'LHE', 'ISB', 'PEW', 'MUX', 'LYP', 'SKT', 'UET', 'GWD', 'DXB', 'DOH', 'JED', 'RUH', 'LHR', 'IST']
const WEATHER = ['Clear', 'Moderate Wind', 'Stormy']

export default function Simulator() {
  const [fleet, setFleet]     = useState([])
  const [loading, setLoading] = useState(true)
  const [tail, setTail]       = useState('')
  const [age, setAge]         = useState(8)
  const [dep, setDep]         = useState('KHI')
  const [arr, setArr]         = useState('LHE')
  const [weather, setWeather] = useState('Clear')
  const [cargo, setCargo]     = useState(15000)
  const [result, setResult]   = useState(null)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    getPakFleet().then(r => {
      const data = r.data.fleet || []
      setFleet(data)
      if (data.length) setTail(data[0].tail_number)
    }).finally(() => setLoading(false))
  }, [])

  const run = async () => {
    setRunning(true); setResult(null)
    try {
      const r = await simulate({ tail_number: tail, aircraft_age_yrs: Number(age),
        departure_iata: dep, arrival_iata: arr, weather, cargo_kg: Number(cargo) })
      setResult(r.data)
    } catch { setResult({ error: true }) }
    finally { setRunning(false) }
  }

  if (loading) return <Page title="Flight Simulator"><Spinner /></Page>

  const p = result?.predictions
  const flags = (result?.risk_flags || []).filter(Boolean)

  return (
    <Page eyebrow="Operations — What-If Analysis" title="Flight Simulator"
      subtitle="Model fuel, emissions, and health impact for a hypothetical flight">

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 16 }}>
        {/* Inputs */}
        <Card>
          <Label>Simulation Parameters</Label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 8 }}>
            <Field label="Aircraft">
              <Select value={tail} onChange={setTail} options={fleet.map(f => f.tail_number)} />
            </Field>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Field label="Departure"><Select value={dep} onChange={setDep} options={AIRPORTS} /></Field>
              <Field label="Arrival"><Select value={arr} onChange={setArr} options={AIRPORTS} /></Field>
            </div>
            <Field label={`Aircraft Age: ${age} years`}>
              <input type="range" min="1" max="25" value={age} onChange={e => setAge(e.target.value)} style={{ width: '100%', accentColor: C.accent }} />
            </Field>
            <Field label={`Cargo Weight: ${Number(cargo).toLocaleString()} kg`}>
              <input type="range" min="0" max="50000" step="1000" value={cargo} onChange={e => setCargo(e.target.value)} style={{ width: '100%', accentColor: C.accent }} />
            </Field>
            <Field label="Weather">
              <div style={{ display: 'flex', gap: 8 }}>
                {WEATHER.map(w => (
                  <button key={w} onClick={() => setWeather(w)} style={{
                    flex: 1, padding: '8px', borderRadius: 8, fontSize: 11, cursor: 'pointer',
                    border: weather === w ? `1px solid ${C.accent}` : `1px solid ${C.border}`,
                    background: weather === w ? `${C.accent}22` : 'transparent',
                    color: weather === w ? C.accent : C.muted }}>{w}</button>
                ))}
              </div>
            </Field>
            <button onClick={run} disabled={running}
              style={{ padding: '12px', borderRadius: 8, border: 'none', cursor: running ? 'wait' : 'pointer',
                       background: C.accent, color: '#fff', fontSize: 13, fontWeight: 600 }}>
              {running ? 'Running simulation...' : 'Run Simulation'}
            </button>
          </div>
        </Card>

        {/* Results */}
        <div>
          {!result ? (
            <Card style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Empty>Configure parameters and run the simulation to see predicted outcomes.</Empty>
            </Card>
          ) : result.error ? (
            <Card><Empty>Simulation failed. Check backend connection.</Empty></Card>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 12 }}>
                <Kpi label="Distance" value={p.distance_km?.toLocaleString()} unit="km" color={C.accent} />
                <Kpi label="Flight Time" value={p.flight_hours} unit="hours" color={C.accent} />
                <Kpi label="Estimated Fuel" value={p.estimated_fuel_litres?.toLocaleString()} unit="litres" color={C.yellow} />
                <Kpi label="Estimated CO₂" value={p.estimated_co2_kg?.toLocaleString()} unit="kg" color={C.yellow} />
              </div>
              <Card>
                <Label>Health Impact</Label>
                <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 28, fontWeight: 700, color: p.health_impact < -5 ? C.red : p.health_impact < 0 ? C.yellow : C.green }}>
                  {p.health_impact}
                </div>
                <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>projected health points from this flight</div>
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${C.border}` }}>
                  <Label>Next Maintenance</Label>
                  <div style={{ fontSize: 14, color: C.text }}>{p.next_maintenance_interval}</div>
                </div>
              </Card>
              {flags.length > 0 && (
                <Card style={{ borderColor: C.yellow }}>
                  <Label>Risk Flags</Label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 }}>
                    {flags.map((f, i) => (
                      <div key={i} style={{ fontSize: 12, color: C.yellow, display: 'flex', gap: 8, alignItems: 'center' }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: C.yellow, flexShrink: 0 }} />{f}
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </Page>
  )
}

function Field({ label, children }) {
  return <div><div style={{ fontSize: 11, color: C.muted, marginBottom: 5 }}>{label}</div>{children}</div>
}
function Select({ value, onChange, options }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{ width: '100%', background: C.bg, border: `1px solid ${C.border}`, color: C.text, padding: '8px 10px', borderRadius: 8, fontSize: 12, cursor: 'pointer' }}>
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  )
}
