import { useState, useEffect } from 'react'
import { getPakFleet, analyzePak, shortAirline, healthColor, riskColor, AIRLINE_ALIAS } from '../api'
import { Page, Card, Label, Badge, Empty, Spinner, C } from '../components/ui'

// Map RUL to a recommended check + days-until-due.
// Lower RUL = sooner. This is a scheduling heuristic on top of the model output.
function schedule(rul) {
  if (rul < 20)  return { check: 'C-check (major)',  days: Math.max(1, Math.round(rul * 0.4)),  color: C.red }
  if (rul < 50)  return { check: 'B-check',          days: Math.round(rul * 0.8),               color: C.yellow }
  if (rul < 100) return { check: 'A-check (routine)', days: Math.round(rul * 1.2),              color: C.accent }
  return { check: 'Line inspection', days: Math.round(rul * 1.5), color: C.green }
}

export default function MaintenanceCal() {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState(0)

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
          const rul = a.data.predicted_rul_cycles
          const sch = schedule(rul)
          out.push({
            tail: p.tail_number, airline: AIRLINE_ALIAS[p.airline] || p.airline,
            type: p.aircraft_type, rul, health: a.data.health_score,
            risk: a.data.risk_level, ...sch,
          })
        } catch { /* skip */ }
        setProgress(Math.round(((i + 1) / fleet.length) * 100))
      }
      if (!cancelled) { setItems(out.sort((x, y) => x.days - y.days)); setLoading(false) }
    })
    return () => { cancelled = true }
  }, [])

  if (loading) return (
    <Page title="Predictive Maintenance Calendar" subtitle="Computing RUL-based schedule across the fleet...">
      <Spinner text={`Analyzing fleet — ${progress}%`} />
    </Page>
  )

  // Bucket into time windows
  const windows = [
    { label: 'This Week (0–7 days)',   min: 0,  max: 7 },
    { label: 'Next Week (8–14 days)',  min: 8,  max: 14 },
    { label: 'This Month (15–30 days)', min: 15, max: 30 },
    { label: 'Upcoming (30+ days)',    min: 31, max: 9999 },
  ]
  const urgent = items.filter(i => i.days <= 7).length

  return (
    <Page eyebrow="Predictive Maintenance — Forward Schedule" title="Maintenance Calendar"
      subtitle="RUL-driven inspection schedule across all 44 aircraft"
      right={<Badge color={urgent > 0 ? C.red : C.green}>{urgent} due this week</Badge>}>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {windows.map(w => {
          const bucket = items.filter(i => i.days >= w.min && i.days <= w.max)
          if (!bucket.length) return null
          return (
            <div key={w.label}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                <span style={{ fontSize: 12, fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase', color: C.muted }}>{w.label}</span>
                <span style={{ fontSize: 11, color: C.dim }}>· {bucket.length} aircraft</span>
                <div style={{ flex: 1, height: 1, background: C.border }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 10 }}>
                {bucket.map(it => (
                  <Card key={it.tail} style={{ borderLeft: `3px solid ${it.color}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                      <div>
                        <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 14, fontWeight: 700, color: C.text }}>{it.tail}</div>
                        <div style={{ fontSize: 10, color: C.dim }}>{it.airline} · {it.type?.split('-')[0]}</div>
                      </div>
                      <Badge color={it.color}>{it.days}d</Badge>
                    </div>
                    <div style={{ fontSize: 13, color: it.color, fontWeight: 500, marginBottom: 6 }}>{it.check}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: C.muted }}>
                      <span>RUL {it.rul} cyc</span>
                      <span>Health {Math.round(it.health)}</span>
                      <Badge color={riskColor(it.risk)}>{it.risk}</Badge>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )
        })}
        {items.length === 0 && <Empty>No schedule data available.</Empty>}
      </div>
      <div style={{ fontSize: 11, color: C.dim, marginTop: 20 }}>
        Schedule derived from each aircraft's LSTM-predicted Remaining Useful Life. Lower RUL brings the recommended check date forward. Final scheduling decisions rest with certified engineers.
      </div>
    </Page>
  )
}
