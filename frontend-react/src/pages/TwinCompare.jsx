import { useState, useEffect } from 'react'
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Legend } from 'recharts'
import { getPakFleet, analyzePak, shortAirline, healthColor, riskColor, AIRLINE_ALIAS } from '../api'
import { Page, Card, Label, Badge, Bar, Spinner, C } from '../components/ui'

export default function TwinCompare() {
  const [fleet, setFleet]   = useState([])
  const [loading, setLoading] = useState(true)
  const [tailA, setTailA]   = useState('')
  const [tailB, setTailB]   = useState('')
  const [a, setA]           = useState(null)
  const [b, setB]           = useState(null)
  const [loadingAB, setLoadingAB] = useState(false)

  useEffect(() => {
    getPakFleet().then(r => {
      const data = r.data.fleet || []
      setFleet(data)
      // pick two same-type aircraft if possible (e.g. two A320s)
      if (data.length >= 2) {
        setTailA(data[0].tail_number)
        const sameType = data.find((p, i) => i > 0 && p.aircraft_type === data[0].aircraft_type)
        setTailB((sameType || data[1]).tail_number)
      }
    }).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!tailA || !tailB) return
    setLoadingAB(true)
    Promise.all([analyzePak(tailA).catch(() => ({ data: null })), analyzePak(tailB).catch(() => ({ data: null }))])
      .then(([ra, rb]) => { setA(ra.data); setB(rb.data) })
      .finally(() => setLoadingAB(false))
  }, [tailA, tailB])

  if (loading) return <Page title="Digital Twin Comparison"><Spinner /></Page>

  const radarData = a && b ? [
    { metric: 'Health', A: a.health_score, B: b.health_score },
    { metric: 'RUL', A: Math.min(100, a.predicted_rul_cycles / 2), B: Math.min(100, b.predicted_rul_cycles / 2) },
    { metric: 'Efficiency', A: Math.max(0, 100 - (a.route_and_emissions?.predicted_fuel_liters || 0) / 10), B: Math.max(0, 100 - (b.route_and_emissions?.predicted_fuel_liters || 0) / 10) },
    { metric: 'Low Emissions', A: Math.max(0, 100 - (a.route_and_emissions?.predicted_co2_kg || 0) / 25), B: Math.max(0, 100 - (b.route_and_emissions?.predicted_co2_kg || 0) / 25) },
    { metric: 'Stability', A: a.anomaly_flag ? 40 : 90, B: b.anomaly_flag ? 40 : 90 },
  ] : []

  return (
    <Page eyebrow="Digital Twin — Side-by-Side Analysis" title="Twin Comparison"
      subtitle="Compare two aircraft of the same type to see how wear affects performance">

      {/* Selectors */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 60px 1fr', gap: 16, marginBottom: 20, alignItems: 'center' }}>
        <Selector label="Aircraft A" value={tailA} onChange={setTailA} fleet={fleet} color={C.accent} />
        <div style={{ textAlign: 'center', fontFamily: 'Orbitron', fontSize: 14, color: C.dim }}>VS</div>
        <Selector label="Aircraft B" value={tailB} onChange={setTailB} fleet={fleet} color={C.yellow} />
      </div>

      {loadingAB ? <Spinner text="Loading both twins..." /> : a && b && (
        <>
          {/* Headline cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <TwinCard d={a} tail={tailA} accent={C.accent} />
            <TwinCard d={b} tail={tailB} accent={C.yellow} />
          </div>

          {/* Radar + metric bars */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Card>
              <Label>Performance Profile</Label>
              <div style={{ height: 320, marginTop: 8 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid stroke={C.border} />
                    <PolarAngleAxis dataKey="metric" tick={{ fill: C.muted, fontSize: 11 }} />
                    <Radar name={tailA} dataKey="A" stroke={C.accent} fill={C.accent} fillOpacity={0.3} />
                    <Radar name={tailB} dataKey="B" stroke={C.yellow} fill={C.yellow} fillOpacity={0.3} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <Label>Head-to-Head Metrics</Label>
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 16 }}>
                <CompareRow label="Health Score" a={a.health_score} b={b.health_score} fmt={v => Math.round(v)} higher />
                <CompareRow label="Predicted RUL (cycles)" a={a.predicted_rul_cycles} b={b.predicted_rul_cycles} higher />
                <CompareRow label="Fuel Burn (L)" a={a.route_and_emissions?.predicted_fuel_liters} b={b.route_and_emissions?.predicted_fuel_liters} fmt={v => v?.toLocaleString()} />
                <CompareRow label="CO₂ (kg)" a={a.route_and_emissions?.predicted_co2_kg} b={b.route_and_emissions?.predicted_co2_kg} fmt={v => v?.toLocaleString()} />
              </div>
              <div style={{ marginTop: 16, paddingTop: 14, borderTop: `1px solid ${C.border}`, fontSize: 12, color: C.muted, lineHeight: 1.6 }}>
                {verdict(a, b, tailA, tailB)}
              </div>
            </Card>
          </div>
        </>
      )}
    </Page>
  )
}

function verdict(a, b, tailA, tailB) {
  const healthier = a.health_score >= b.health_score ? tailA : tailB
  const diff = Math.abs(Math.round(a.health_score - b.health_score))
  if (diff < 3) return `${tailA} and ${tailB} are in comparable condition. Either is a sound operational choice today.`
  return `${healthier} is the healthier airframe by ${diff} health points and carries a higher remaining useful life, making it the lower-risk choice for demanding routes. The difference reflects accumulated engine wear between the two aircraft.`
}

function Selector({ label, value, onChange, fleet, color }) {
  return (
    <div>
      <div style={{ fontSize: 11, color, marginBottom: 5, fontWeight: 600 }}>{label}</div>
      <select value={value} onChange={e => onChange(e.target.value)}
        style={{ width: '100%', background: C.card, border: `1px solid ${color}66`, color: C.text, padding: '10px 14px', borderRadius: 8, fontSize: 13, cursor: 'pointer' }}>
        {fleet.map(p => <option key={p.tail_number} value={p.tail_number}>{p.tail_number} — {p.aircraft_type?.split('-')[0]} ({shortAirline(p.airline)})</option>)}
      </select>
    </div>
  )
}

function TwinCard({ d, tail, accent }) {
  return (
    <Card style={{ borderTop: `3px solid ${accent}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 20, fontWeight: 700, color: C.text }}>{tail}</div>
          <div style={{ fontSize: 12, color: C.muted }}>{d.aircraft_type} · {shortAirline(d.airline)}</div>
        </div>
        <Badge color={riskColor(d.risk_level)}>{d.risk_level}</Badge>
      </div>
      <div style={{ display: 'flex', gap: 24, marginTop: 16 }}>
        <div>
          <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase' }}>Health</div>
          <div style={{ fontFamily: 'Orbitron', fontSize: 30, fontWeight: 700, color: healthColor(d.health_score) }}>{Math.round(d.health_score)}</div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase' }}>RUL</div>
          <div style={{ fontFamily: 'Orbitron', fontSize: 30, fontWeight: 700, color: accent }}>{d.predicted_rul_cycles}</div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', marginBottom: 6 }}>Health Bar</div>
          <Bar value={d.health_score} color={healthColor(d.health_score)} height={8} />
          <div style={{ fontSize: 10, color: C.dim, marginTop: 8 }}>Phase: {d.flight_phase} · {d.live_telemetry?.alt_m}m</div>
        </div>
      </div>
    </Card>
  )
}

function CompareRow({ label, a, b, fmt = v => v, higher = false }) {
  const aWins = higher ? a >= b : a <= b
  return (
    <div>
      <div style={{ fontSize: 11, color: C.muted, marginBottom: 4, textAlign: 'center' }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ flex: 1, textAlign: 'right', fontFamily: 'Orbitron', fontSize: 15, fontWeight: 700, color: aWins ? C.green : C.muted }}>{fmt(a) ?? '—'}</div>
        <div style={{ width: 30, textAlign: 'center', fontSize: 10, color: C.dim }}>vs</div>
        <div style={{ flex: 1, textAlign: 'left', fontFamily: 'Orbitron', fontSize: 15, fontWeight: 700, color: !aWins ? C.green : C.muted }}>{fmt(b) ?? '—'}</div>
      </div>
    </div>
  )
}
