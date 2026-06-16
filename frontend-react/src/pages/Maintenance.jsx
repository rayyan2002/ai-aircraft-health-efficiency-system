import { useState, useEffect } from 'react'
import { getPakFleet, analyzePak, getMaintHistory, logMaintenance, shortAirline, healthColor, riskColor, AIRLINE_ALIAS } from '../api'
import { Page, Card, Label, Pill, Badge, Bar, Empty, Spinner, C } from '../components/ui'

const COMPONENTS = ['Engine 1', 'Engine 2', 'APU', 'Landing Gear', 'Avionics', 'Windshield', 'Fuel System']
const TYPES = ['A-check', 'B-check', 'C-check', 'Component replacement', 'Inspection']
const LOCATIONS = ['KHI', 'LHE', 'ISB', 'PEW', 'MUX', 'SKT']
const FILTERS = ['All', 'PIA', 'AirBlue', 'AirSial', 'FlyJinnah']

export default function Maintenance() {
  const [fleet, setFleet]       = useState([])
  const [filter, setFilter]     = useState('All')
  const [tail, setTail]         = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [history, setHistory]   = useState([])
  const [loading, setLoading]   = useState(true)

  const [component, setComponent] = useState(COMPONENTS[0])
  const [mtype, setMtype]         = useState(TYPES[0])
  const [location, setLocation]   = useState(LOCATIONS[0])
  const [notes, setNotes]         = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [toast, setToast]         = useState('')

  useEffect(() => {
    getPakFleet().then(r => {
      const data = r.data.fleet || []
      setFleet(data)
      if (data.length) setTail(data[0].tail_number)
    }).finally(() => setLoading(false))
  }, [])

  const loadAircraft = (t) => {
    if (!t) return
    setAnalysis(null)
    Promise.all([analyzePak(t).catch(() => ({ data: null })), getMaintHistory(t).catch(() => ({ data: { records: [] } }))])
      .then(([a, h]) => { setAnalysis(a.data); setHistory(h.data.records || []) })
  }
  useEffect(() => { loadAircraft(tail) }, [tail])

  const filtered = fleet.filter(p => filter === 'All' || (AIRLINE_ALIAS[p.airline] || p.airline) === filter)

  const submit = async () => {
    setSubmitting(true); setToast('')
    try {
      const r = await logMaintenance({ tail_number: tail, component, maintenance_type: mtype, location, notes })
      setToast(r.data.message || 'Maintenance logged successfully.')
      setNotes('')
      loadAircraft(tail)
    } catch (e) {
      setToast('Failed to log maintenance. Check backend connection.')
    } finally {
      setSubmitting(false)
      setTimeout(() => setToast(''), 5000)
    }
  }

  const health = analysis?.health_score ?? 50
  const rul    = analysis?.predicted_rul_cycles ?? '—'
  const risk   = analysis?.risk_level ?? '—'

  if (loading) return <Page title="Maintenance Portal"><Spinner /></Page>

  return (
    <Page eyebrow="Engineering — Maintenance Operations" title="Maintenance Portal"
      subtitle="Log service actions and track maintenance history across the fleet">

      {/* Filter + selector */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        {FILTERS.map(f => <Pill key={f} active={filter === f} onClick={() => setFilter(f)}>{f}</Pill>)}
        <select value={tail} onChange={e => setTail(e.target.value)}
          style={{ marginLeft: 'auto', background: C.card, border: `1px solid ${C.border}`, color: C.text, padding: '7px 14px', borderRadius: 8, fontSize: 12, minWidth: 220, cursor: 'pointer' }}>
          {filtered.map(p => <option key={p.tail_number} value={p.tail_number}>{p.tail_number} — {p.aircraft_type?.split('-')[0]}</option>)}
        </select>
      </div>

      {/* Current status */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr', gap: 12, marginBottom: 20 }}>
        <Card>
          <Label>Aircraft</Label>
          <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 22, fontWeight: 700, color: C.text }}>{tail}</div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>{analysis?.aircraft_type} · {shortAirline(analysis?.airline)}</div>
        </Card>
        <Card>
          <Label>Current Health</Label>
          <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 26, fontWeight: 700, color: healthColor(health) }}>{Math.round(health)}</div>
          <div style={{ marginTop: 8 }}><Bar value={health} color={healthColor(health)} /></div>
        </Card>
        <Card>
          <Label>RUL · Risk</Label>
          <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 22, fontWeight: 700, color: C.text }}>{rul}<span style={{ fontSize: 12, color: C.dim }}> cyc</span></div>
          <div style={{ marginTop: 6 }}><Badge color={riskColor(risk)}>{risk}</Badge></div>
        </Card>
      </div>

      {/* Log form + history */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: 16 }}>
        {/* Form */}
        <Card>
          <Label>Log New Maintenance</Label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 8 }}>
            <Field label="Component">
              <Select value={component} onChange={setComponent} options={COMPONENTS} />
            </Field>
            <Field label="Maintenance Type">
              <Select value={mtype} onChange={setMtype} options={TYPES} />
            </Field>
            <Field label="Location">
              <Select value={location} onChange={setLocation} options={LOCATIONS} />
            </Field>
            <Field label="Notes (optional)">
              <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3}
                placeholder="Describe the work performed..."
                style={{ background: C.bg, border: `1px solid ${C.border}`, color: C.text, padding: '8px 10px', borderRadius: 8, fontSize: 12, resize: 'vertical', fontFamily: 'Inter' }} />
            </Field>
            <button onClick={submit} disabled={submitting}
              style={{ padding: '11px', borderRadius: 8, border: 'none', cursor: submitting ? 'wait' : 'pointer',
                       background: C.accent, color: '#fff', fontSize: 13, fontWeight: 600 }}>
              {submitting ? 'Logging...' : 'Log Maintenance & Reset Health'}
            </button>
            {toast && <div style={{ fontSize: 12, color: C.green, padding: '8px 10px', background: 'rgba(63,185,80,0.08)', borderRadius: 8, border: `1px solid ${C.green}44` }}>{toast}</div>}
          </div>
        </Card>

        {/* History */}
        <Card>
          <Label>Maintenance History</Label>
          {history.length === 0 ? <Empty>No maintenance records for {tail} yet.</Empty> : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
              {history.map(rec => (
                <div key={rec.id} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 8, padding: '10px 14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>{rec.component}</span>
                    <Badge color={C.accent}>{rec.maintenance_type}</Badge>
                  </div>
                  <div style={{ fontSize: 11, color: C.muted }}>{rec.location} · {(rec.performed_at || '').slice(0, 16).replace('T', ' ')}</div>
                  {rec.notes && <div style={{ fontSize: 11, color: C.dim, marginTop: 4 }}>{rec.notes}</div>}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </Page>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: C.muted, marginBottom: 5 }}>{label}</div>
      {children}
    </div>
  )
}
function Select({ value, onChange, options }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{ width: '100%', background: C.bg, border: `1px solid ${C.border}`, color: C.text, padding: '8px 10px', borderRadius: 8, fontSize: 12, cursor: 'pointer' }}>
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  )
}
