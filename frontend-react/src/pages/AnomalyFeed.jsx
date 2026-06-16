import { useState, useEffect } from 'react'
import { getPakFleet, analyzePak, shortAirline, riskColor, AIRLINE_ALIAS } from '../api'
import { Page, Card, Label, Badge, Empty, Spinner, C } from '../components/ui'

function severity(item) {
  if (item.anomaly_flag === 1) return { level: 'CRITICAL', color: C.red, rank: 3 }
  if (item.risk === 'High')    return { level: 'HIGH',     color: C.red, rank: 3 }
  if (item.risk === 'Moderate')return { level: 'WARNING',  color: C.yellow, rank: 2 }
  return { level: 'INFO', color: C.accent, rank: 1 }
}

export default function AnomalyFeed() {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState(0)
  const [filter, setFilter]   = useState('alerts') // 'alerts' | 'all'

  useEffect(() => {
    let cancelled = false
    getPakFleet().then(async r => {
      const fleet = r.data.fleet || []
      const out = []
      for (let i = 0; i < fleet.length; i++) {
        if (cancelled) return
        const p = fleet[i]
        try {
          const a = await analyzePak(p.tail_number)
          const d = a.data
          out.push({
            tail: p.tail_number, airline: AIRLINE_ALIAS[p.airline] || p.airline,
            type: p.aircraft_type, risk: d.risk_level, health: d.health_score,
            rul: d.predicted_rul_cycles, anomaly_flag: d.anomaly_flag,
            score: d.iforest_score, phase: d.flight_phase,
            alt: d.live_telemetry?.alt_m, speed: d.live_telemetry?.speed_ms,
          })
        } catch { /* skip */ }
        setProgress(Math.round(((i + 1) / fleet.length) * 100))
      }
      if (!cancelled) {
        out.sort((x, y) => severity(y).rank - severity(x).rank || x.health - y.health)
        setItems(out); setLoading(false)
      }
    })
    return () => { cancelled = true }
  }, [])

  if (loading) return (
    <Page title="Anomaly Alert Feed" subtitle="Scanning fleet for anomalies...">
      <Spinner text={`Scanning — ${progress}%`} />
    </Page>
  )

  const alerts = items.filter(i => severity(i).rank >= 2 || i.anomaly_flag === 1)
  const shown = filter === 'alerts' ? alerts : items
  const counts = {
    critical: items.filter(i => severity(i).rank === 3).length,
    warning: items.filter(i => severity(i).level === 'WARNING').length,
    normal: items.filter(i => severity(i).rank === 1 && i.anomaly_flag !== 1).length,
  }

  return (
    <Page eyebrow="Operations Center — Real-Time Monitoring" title="Anomaly Alert Feed"
      subtitle="Isolation Forest flags and health-based alerts across the fleet"
      right={
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setFilter('alerts')} style={pillStyle(filter === 'alerts')}>Alerts ({alerts.length})</button>
          <button onClick={() => setFilter('all')} style={pillStyle(filter === 'all')}>All ({items.length})</button>
        </div>
      }>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginBottom: 20 }}>
        <Card style={{ borderLeft: `3px solid ${C.red}` }}>
          <Label>Critical / High</Label>
          <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 28, fontWeight: 700, color: C.red }}>{counts.critical}</div>
        </Card>
        <Card style={{ borderLeft: `3px solid ${C.yellow}` }}>
          <Label>Warnings</Label>
          <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 28, fontWeight: 700, color: C.yellow }}>{counts.warning}</div>
        </Card>
        <Card style={{ borderLeft: `3px solid ${C.green}` }}>
          <Label>Normal</Label>
          <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 28, fontWeight: 700, color: C.green }}>{counts.normal}</div>
        </Card>
      </div>

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {shown.length === 0 ? <Empty>No active alerts. All aircraft operating within normal parameters.</Empty> :
          shown.map((it, i) => {
            const sev = severity(it)
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '14px 18px', borderBottom: `1px solid ${C.border}` }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: sev.color, flexShrink: 0, boxShadow: `0 0 8px ${sev.color}` }} />
                <div style={{ width: 80 }}><Badge color={sev.color}>{sev.level}</Badge></div>
                <div style={{ width: 100, fontFamily: 'Orbitron, monospace', fontSize: 13, color: C.text }}>{it.tail}</div>
                <div style={{ flex: 1, fontSize: 12, color: C.muted }}>
                  {it.anomaly_flag === 1
                    ? `ADS-B anomaly detected (score ${it.score}) during ${it.phase} phase`
                    : it.risk === 'High'  ? `Low remaining useful life — RUL ${it.rul} cycles, health ${Math.round(it.health)}`
                    : it.risk === 'Moderate' ? `Elevated wear — RUL ${it.rul} cycles, monitor closely`
                    : `Nominal — RUL ${it.rul} cycles, health ${Math.round(it.health)}`}
                </div>
                <div style={{ fontSize: 10, color: C.dim, width: 90, textAlign: 'right' }}>{it.airline}</div>
              </div>
            )
          })}
      </Card>
      <div style={{ fontSize: 11, color: C.dim, marginTop: 16 }}>
        Anomaly flags come from the Isolation Forest model applied to live flight telemetry. Risk levels combine predicted RUL and anomaly status.
      </div>
    </Page>
  )
}

function pillStyle(active) {
  return {
    padding: '6px 14px', borderRadius: 20, fontSize: 11, cursor: 'pointer',
    border: active ? `1px solid ${C.accent}` : `1px solid ${C.border}`,
    background: active ? `${C.accent}22` : 'transparent',
    color: active ? C.accent : C.muted,
  }
}
