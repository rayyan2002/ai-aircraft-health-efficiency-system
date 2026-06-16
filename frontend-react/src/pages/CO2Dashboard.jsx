import { useState, useEffect } from 'react'
import { BarChart, Bar as RBar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import { getPakFleet, shortAirline, AIRLINE_ALIAS, AIRLINE_COLOR } from '../api'
import { Page, Card, Label, Kpi, Empty, Spinner, C } from '../components/ui'

// Per-airline average annual hours (from fleet seed assumptions) used to estimate emissions.
// CO2 (kg/yr) = annual_hours * avg_burn_lph * 2.53. Avg burn varies by type.
const BURN_LPH = { 'A320': 2500, 'A321': 2900, 'B777': 6800, default: 2700 }
const ANNUAL_HOURS = { PIA: 3300, AirBlue: 3500, AirSial: 3200, FlyJinnah: 3200, default: 3200 }

function estimateCO2(plane) {
  const type = plane.aircraft_type || ''
  let burn = BURN_LPH.default
  if (type.includes('777')) burn = BURN_LPH.B777
  else if (type.includes('321')) burn = BURN_LPH.A321
  else if (type.includes('320')) burn = BURN_LPH.A320
  const al = AIRLINE_ALIAS[plane.airline] || plane.airline
  const hrs = ANNUAL_HOURS[al] || ANNUAL_HOURS.default
  return (hrs * burn * 2.53) / 1000 // tonnes/year
}

export default function CO2Dashboard() {
  const [fleet, setFleet]     = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getPakFleet().then(r => setFleet(r.data.fleet || [])).finally(() => setLoading(false))
  }, [])

  if (loading) return <Page title="CO₂ ESG Dashboard"><Spinner /></Page>

  // Aggregate by airline
  const byAirline = {}
  fleet.forEach(p => {
    const al = AIRLINE_ALIAS[p.airline] || p.airline
    if (!byAirline[al]) byAirline[al] = { airline: al, co2: 0, count: 0 }
    byAirline[al].co2 += estimateCO2(p)
    byAirline[al].count += 1
  })
  const airlineData = Object.values(byAirline).map(a => ({ ...a, co2: Math.round(a.co2) }))
  const totalCO2 = Math.round(airlineData.reduce((s, a) => s + a.co2, 0))
  const totalTrees = Math.round(totalCO2 * 1000 / 21) // ~21kg CO2 absorbed per tree/year
  const avgPerAircraft = fleet.length ? Math.round(totalCO2 / fleet.length) : 0

  const pieColors = { PIA: '#388bfd', AirBlue: '#3fb950', AirSial: '#d29922', FlyJinnah: '#f85149' }

  return (
    <Page eyebrow="Environmental, Social & Governance" title="CO₂ ESG Dashboard"
      subtitle="Estimated annual carbon footprint across Pakistan's commercial fleet">

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 20 }}>
        <Kpi label="Total Fleet CO₂" value={totalCO2.toLocaleString()} unit="tonnes / year" color={C.yellow} />
        <Kpi label="Avg per Aircraft" value={avgPerAircraft.toLocaleString()} unit="tonnes / year" color={C.accent} />
        <Kpi label="Aircraft Tracked" value={fleet.length} unit="commercial fleet" color={C.green} />
        <Kpi label="Trees to Offset" value={totalTrees.toLocaleString()} unit="trees / year" color={C.green} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 16, marginBottom: 20 }}>
        <Card>
          <Label>Annual CO₂ by Airline (tonnes)</Label>
          <div style={{ height: 300, marginTop: 12 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={airlineData}>
                <XAxis dataKey="airline" tick={{ fill: C.muted, fontSize: 11 }} axisLine={{ stroke: C.border }} />
                <YAxis tick={{ fill: C.muted, fontSize: 11 }} axisLine={{ stroke: C.border }} />
                <Tooltip contentStyle={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text }} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <RBar dataKey="co2" radius={[6, 6, 0, 0]}>
                  {airlineData.map((a, i) => <Cell key={i} fill={pieColors[a.airline] || C.accent} />)}
                </RBar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <Label>Fleet Share of Emissions</Label>
          <div style={{ height: 300, marginTop: 12 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={airlineData} dataKey="co2" nameKey="airline" cx="50%" cy="50%" outerRadius={90} innerRadius={50}>
                  {airlineData.map((a, i) => <Cell key={i} fill={pieColors[a.airline] || C.accent} />)}
                </Pie>
                <Legend wrapperStyle={{ fontSize: 11, color: C.muted }} />
                <Tooltip contentStyle={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card>
        <Label>Per-Airline Breakdown</Label>
        <div style={{ marginTop: 8 }}>
          {airlineData.sort((a, b) => b.co2 - a.co2).map(a => (
            <div key={a.airline} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 120px', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: `1px solid ${C.border}` }}>
              <span style={{ fontSize: 13, color: pieColors[a.airline] || C.text, fontWeight: 500 }}>{a.airline}</span>
              <div style={{ height: 8, background: C.border, borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${(a.co2 / totalCO2) * 100}%`, background: pieColors[a.airline] || C.accent, borderRadius: 4 }} />
              </div>
              <span style={{ fontSize: 12, color: C.muted, textAlign: 'right' }}>{a.co2.toLocaleString()} t · {a.count} ac</span>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 11, color: C.dim, marginTop: 12 }}>
          Estimates based on aircraft type, per-airline average annual utilisation, and the ICAO Jet-A emission factor (2.53 kg CO₂ per litre of fuel).
        </div>
      </Card>
    </Page>
  )
}
