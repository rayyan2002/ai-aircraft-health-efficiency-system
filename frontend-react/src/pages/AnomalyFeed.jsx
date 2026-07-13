import { useState, useEffect } from 'react'
import { getFleetHealth, getLiveMap, riskColor, AIRLINE_ALIAS, toIATA } from '../api'
import { Page, Card, Label, Badge, Empty, Spinner, C } from '../components/ui'
import RecomputeButton from '../components/RecomputeButton'

function severity(it) {
  if (it.anomaly)               return { level: 'CRITICAL', color: C.red,    rank: 3 }
  if (it.risk === 'High')       return { level: 'HIGH',     color: C.red,    rank: 3 }
  if (it.risk === 'Moderate')   return { level: 'WARNING',  color: C.yellow, rank: 2 }
  return { level: 'NOMINAL', color: C.green, rank: 1 }
}

export default function AnomalyFeed() {
  const [health,  setHealth]  = useState([])   // from cached fleet_health
  const [live,    setLive]    = useState([])   // from live_map (real IForest flags)
  const [loading, setLoading] = useState(true)
  const [filter,  setFilter]  = useState('alerts')

  const loadLive = () => getLiveMap()
    .then(r => setLive(r.data.aircraft || []))
    .catch(() => setLive([]))

  useEffect(() => {
    Promise.all([
      getFleetHealth().then(r => setHealth(r.data.fleet || [])).catch(() => setHealth([])),
      loadLive(),
    ]).finally(() => setLoading(false))

    const iv = setInterval(loadLive, 20000)   // anomaly state is live
    return () => clearInterval(iv)
  }, [])

  if (loading) return <Page title="Anomaly Alert Feed"><Spinner text="Loading fleet…" /></Page>

  // Join: health (all 44) + live anomaly state (airborne only)
  const liveByTail = {}
  for (const a of live) {
    if (a.tail_number) liveByTail[a.tail_number] = a
  }

  const items = health.map(h => {
    const l = liveByTail[h.tail_number]
    return {
      tail:     h.tail_number,
      airline:  AIRLINE_ALIAS[h.airline] || h.airline,
      type:     h.aircraft_type,
      health:   h.health_score,
      rul:      h.predicted_rul_cycles,
      risk:     h.risk_level,
      airborne: !!l,
      anomaly:  !!(l && l.anomaly),
      callsign: l?.callsign,
      alt:      l?.altitude,
      speed:    l?.velocity,
    }
  }).sort((a, b) =>
    severity(b).rank - severity(a).rank ||
    (a.health ?? 100) - (b.health ?? 100)
  )

  const alerts = items.filter(i => severity(i).rank >= 2)
  const shown  = filter === 'alerts' ? alerts : items

  const counts = {
    critical: items.filter(i => severity(i).rank === 3).length,
    warning:  items.filter(i => severity(i).level === 'WARNING').length,
    nominal:  items.filter(i => severity(i).rank === 1).length,
    airborne: items.filter(i => i.airborne).length,
  }

  const pill = (active) => ({
    padding: '6px 14px', borderRadius: 20, fontSize: 11, cursor: 'pointer',
    border: active ? `1px solid ${C.accent}` : `1px solid ${C.border}`,
    background: active ? 'rgba(56,139,253,0.15)' : 'transparent',
    color: active ? C.accent : C.muted,
  })

  return (
    <Page
      eyebrow="Operations Center — Real-Time Monitoring"
      title="Anomaly Alert Feed"
      subtitle="Isolation Forest flags on live flights, combined with engine-health risk"
      right={
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setFilter('alerts')} style={pill(filter === 'alerts')}>
              Alerts ({alerts.length})
            </button>
            <button onClick={() => setFilter('all')} style={pill(filter === 'all')}>
              All ({items.length})
            </button>
          </div>
          <RecomputeButton onDone={setHealth} />
        </div>
      }
    >
      {/* Counters */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Critical / High', value: counts.critical, color: C.red },
          { label: 'Warnings',        value: counts.warning,  color: C.yellow },
          { label: 'Nominal',         value: counts.nominal,  color: C.green },
          { label: 'Airborne Now',    value: counts.airborne, color: C.accent },
        ].map(({ label, value, color }) => (
          <Card key={label} style={{ borderLeft: `3px solid ${color}` }}>
            <Label>{label}</Label>
            <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 28, fontWeight: 700, color }}>
              {value}
            </div>
          </Card>
        ))}
      </div>

      {/* Feed */}
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {shown.length === 0 ? (
          <Empty>No active alerts. All aircraft within normal parameters.</Empty>
        ) : shown.map((it, i) => {
          const sev = severity(it)
          return (
            <div key={it.tail} style={{
              display: 'flex', alignItems: 'center', gap: 14,
              padding: '13px 18px', borderBottom: `1px solid ${C.border}`,
            }}>
              <div style={{
                width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                background: sev.color, boxShadow: `0 0 8px ${sev.color}`,
              }} />
              <div style={{ width: 82 }}><Badge color={sev.color}>{sev.level}</Badge></div>
              <div style={{ width: 96, fontFamily: 'Orbitron, monospace', fontSize: 13, color: C.text }}>
                {it.tail}
              </div>
              <div style={{ width: 80 }}>
                {it.airborne ? (
                  <span style={{ fontSize: 10, fontFamily: 'Orbitron, monospace', color: '#3fb950' }}>
                    ✈ {toIATA(it.callsign || '')}
                  </span>
                ) : (
                  <span style={{ fontSize: 10, color: C.dim }}>grounded</span>
                )}
              </div>
              <div style={{ flex: 1, fontSize: 12, color: C.muted }}>
                {it.anomaly
                  ? `Isolation Forest flagged abnormal flight dynamics at ${Math.round(it.alt || 0)} m, ${(it.speed || 0).toFixed(0)} m/s`
                  : it.risk === 'High'
                    ? `Low remaining useful life — RUL ${it.rul} cycles, health ${Math.round(it.health ?? 0)}`
                    : it.risk === 'Moderate'
                      ? `Elevated engine wear — RUL ${it.rul} cycles, monitor closely`
                      : `Nominal — RUL ${it.rul} cycles, health ${Math.round(it.health ?? 0)}`}
              </div>
              <div style={{ fontSize: 10, color: C.dim, width: 84, textAlign: 'right' }}>
                {it.airline}
              </div>
            </div>
          )
        })}
      </Card>

      <div style={{ fontSize: 11, color: C.dim, marginTop: 16, lineHeight: 1.6 }}>
        Anomaly flags come from the Isolation Forest model, which scores live ADS-B telemetry
        (altitude, speed, vertical rate, track) as each reading is ingested. Only airborne aircraft
        can carry a live anomaly flag — a grounded aircraft has no live telemetry to score.
        Risk combines that flag with predicted engine Remaining Useful Life.
      </div>
    </Page>
  )
}