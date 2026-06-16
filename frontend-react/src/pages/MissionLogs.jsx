import { useState, useEffect } from 'react'
import { getPakFleet, getPakHistory, shortAirline, healthColor, AIRLINE_ALIAS } from '../api'
import { Page, Card, Label, Pill, Badge, Empty, Spinner, C } from '../components/ui'

const FILTERS = ['All', 'PIA', 'AirBlue', 'AirSial', 'FlyJinnah']

export default function MissionLogs() {
  const [fleet, setFleet]     = useState([])
  const [filter, setFilter]   = useState('All')
  const [tail, setTail]       = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [hLoading, setHLoading] = useState(false)

  useEffect(() => {
    getPakFleet().then(r => {
      const data = r.data.fleet || []
      setFleet(data)
      if (data.length) setTail(data[0].tail_number)
    }).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!tail) return
    setHLoading(true)
    getPakHistory(tail).then(r => setHistory(r.data.history || []))
      .catch(() => setHistory([]))
      .finally(() => setHLoading(false))
  }, [tail])

  const filtered = fleet.filter(p => filter === 'All' || (AIRLINE_ALIAS[p.airline] || p.airline) === filter)

  const exportCSV = () => {
    if (!history.length) return
    const header = 'Flight ID,Date,Route,Fuel (L),CO2 (kg),Health\n'
    const rows = history.map(h => `${h.flight_id},${h.date},${h.route},${h.fuel_consumed},${h.co2_emissions},${h.health_score}`).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${tail}_mission_logs.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) return <Page title="Mission Logs"><Spinner /></Page>

  return (
    <Page eyebrow="Operations — Flight History" title="Mission Logs"
      subtitle="Completed flight records, fuel burn, and emissions per aircraft"
      right={history.length > 0 && <button onClick={exportCSV} style={{ padding: '8px 16px', borderRadius: 8, border: `1px solid ${C.border}`, background: 'transparent', color: C.accent, fontSize: 12, cursor: 'pointer' }}>Export CSV</button>}>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        {FILTERS.map(f => <Pill key={f} active={filter === f} onClick={() => setFilter(f)}>{f}</Pill>)}
        <select value={tail} onChange={e => setTail(e.target.value)}
          style={{ marginLeft: 'auto', background: C.card, border: `1px solid ${C.border}`, color: C.text, padding: '7px 14px', borderRadius: 8, fontSize: 12, minWidth: 220, cursor: 'pointer' }}>
          {filtered.map(p => <option key={p.tail_number} value={p.tail_number}>{p.tail_number} — {p.aircraft_type?.split('-')[0]}</option>)}
        </select>
      </div>

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.4fr 2fr 1fr 1fr 1fr', padding: '12px 18px', borderBottom: `1px solid ${C.border}`, background: C.hover }}>
          {['Flight ID', 'Date', 'Route', 'Fuel (L)', 'CO₂ (kg)', 'Health'].map(h => (
            <div key={h} style={{ fontSize: 10, fontWeight: 600, letterSpacing: 1.5, textTransform: 'uppercase', color: C.muted }}>{h}</div>
          ))}
        </div>
        {hLoading ? <Spinner /> : history.length === 0 ? (
          <Empty>No completed flights logged for {tail} yet.<br /><span style={{ fontSize: 11 }}>Flight history populates as the absence-detection pipeline logs landings.</span></Empty>
        ) : history.map((h, i) => (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.4fr 2fr 1fr 1fr 1fr', padding: '12px 18px', borderBottom: `1px solid ${C.border}`, alignItems: 'center', fontSize: 13 }}>
            <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 11, color: C.accent }}>{h.flight_id}</div>
            <div style={{ color: C.muted, fontSize: 12 }}>{h.date}</div>
            <div style={{ color: C.text }}>{h.route}</div>
            <div style={{ color: C.text }}>{h.fuel_consumed?.toLocaleString() || '—'}</div>
            <div style={{ color: C.text }}>{h.co2_emissions?.toLocaleString() || '—'}</div>
            <div><Badge color={healthColor(h.health_score || 0)}>{Math.round(h.health_score || 0)}</Badge></div>
          </div>
        ))}
      </Card>
    </Page>
  )
}
