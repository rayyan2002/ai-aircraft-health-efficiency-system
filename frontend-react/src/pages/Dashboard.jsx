import { useState, useEffect } from 'react'
import { getLiveFleet, analyzeLive, getLiveMap, getLiveTrack, toIATA } from '../api'
import { Page, Card, Label, Kpi, Badge, Bar, Empty, Spinner, C } from '../components/ui'
import LiveMap from '../components/LiveMap'

export default function Dashboard() {
  const [fleet, setFleet]       = useState([])
  const [sel, setSel]           = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading]   = useState(false)
  const [fleetLoad, setFleetLoad] = useState(true)
  const [noLive, setNoLive]     = useState(false)
  const [scope, setScope]       = useState('pak')   // 'pak' | 'all'
  const [counts, setCounts]     = useState({ pakistani_count: 0, foreign_count: 0, in_fleet_count: 0 })
  const [mapAircraft, setMapAircraft] = useState([])
  const [trail, setTrail]       = useState([])

  useEffect(() => {
    const load = () => getLiveFleet().then(r => {
      const list = r.data.fleet || []
      if (list.length && list[0].tail_number !== 'No live flights' && list[0].tail_number !== 'Error') {
        setFleet(list); setNoLive(false)
        setCounts({ pakistani_count: r.data.pakistani_count || 0, foreign_count: r.data.foreign_count || 0, in_fleet_count: r.data.in_fleet_count || 0 })
        setSel(prev => prev || list[0].tail_number)
      } else {
        setFleet([]); setNoLive(true)
      }
    }).catch(() => setNoLive(true)).finally(() => setFleetLoad(false))
    load()
    const loadMap = () => getLiveMap()
      .then(r => setMapAircraft(r.data.aircraft || []))
      .catch(() => setMapAircraft([]))
    loadMap()
    const iv  = setInterval(load, 30000)
    const iv2 = setInterval(loadMap, 20000)
    return () => { clearInterval(iv); clearInterval(iv2) }
  }, [])

  useEffect(() => {
    if (!sel) return
    setLoading(true); setAnalysis(null); setTrail([])
    Promise.all([
      analyzeLive(sel).catch(() => ({ data: null })),
      getLiveTrack(sel).catch(() => ({ data: { points: [] } })),
    ]).then(([a, t]) => {
      setAnalysis(a.data)
      setTrail(t.data?.points || [])
    }).finally(() => setLoading(false))
  }, [sel])

  const shown   = scope === 'pak' ? fleet.filter(f => f.is_pakistani) : fleet
  const lt      = analysis?.live_telemetry || {}
  const lat     = lt.lat || 30.3753
  const lon     = lt.lon || 69.3451
  const anomaly = analysis?.anomaly_flag === 1
  const score   = analysis?.iforest_score
  const statusColor = anomaly ? C.red : C.green

  return (
    <Page eyebrow="OpenSky Network — Real-Time ADS-B" title="Live Anomaly Monitor"
      subtitle="Real-time flight-behaviour monitoring and anomaly detection over the region"
      right={<Badge color={noLive ? C.yellow : C.green}>{noLive ? 'No live flights' : `${counts.pakistani_count} PK flights \u00b7 ${counts.in_fleet_count} in tracked fleet \u00b7 ${counts.foreign_count} foreign`}</Badge>}>

      {/* Scope note — sets expectations honestly */}
      <div style={{ background: 'rgba(56,139,253,0.06)', border: `1px solid ${C.border}`, borderRadius: 10, padding: '12px 16px', marginBottom: 20, fontSize: 12, color: C.muted, lineHeight: 1.6 }}>
        This monitor tracks <strong style={{ color: C.text }}>live aircraft broadcasting ADS-B</strong> over the region via the OpenSky Network and runs each through the Isolation Forest model to flag abnormal flight behaviour in real time.
        Engine Remaining-Useful-Life prediction is not shown here — RUL depends on accumulated engine cycles, which are only available for the 44 curated aircraft on the <strong style={{ color: C.accent }}>Pakistan Fleet</strong> page.
        <br /><span style={{ color: C.dim }}>Note: ADS-B broadcasts position but not route, so origin and destination are not available from this feed.</span>
      </div>

      {fleetLoad ? <Spinner text="Connecting to live feed..." /> : noLive ? (
        <Card>
          <Empty>
            No aircraft are currently broadcasting live ADS-B over the region.<br />
            This is normal on the free OpenSky tier — coverage over Pakistan is sparse and the feed updates as flights pass overhead.<br />
            <span style={{ color: C.muted }}>For continuous fleet monitoring, use the Pakistan Fleet page.</span>
          </Empty>
        </Card>
      ) : (
        <>
          {/* Selector */}
          <div style={{ marginBottom: 20, display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div>
              <Label>Airspace Scope</Label>
              <div style={{ display: 'flex', gap: 8 }}>
                {[['pak', `Pakistani carriers (${counts.pakistani_count})`],
                  ['all', `All aircraft in airspace (${counts.pakistani_count + counts.foreign_count})`]].map(([k, lbl]) => (
                  <button key={k} onClick={() => { setScope(k); setSel('') }}
                    style={{
                      padding: '8px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer',
                      border: scope === k ? `1px solid ${C.accent}` : `1px solid ${C.border}`,
                      background: scope === k ? 'rgba(56,139,253,0.15)' : 'transparent',
                      color: scope === k ? C.accent : C.muted,
                    }}>{lbl}</button>
                ))}
              </div>
            </div>
            <div>
              <Label>Select Live Flight</Label>
              <select value={sel} onChange={e => setSel(e.target.value)}
                style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text,
                         padding: '8px 14px', borderRadius: 8, fontSize: 13, minWidth: 300, cursor: 'pointer' }}>
                <option value="">— Select a flight —</option>
                {shown.map(f => (
                  <option key={f.tail_number} value={f.tail_number}>
                    {toIATA(f.tail_number)} ({f.tail_number}){f.is_pakistani ? '' : '  \u2708 foreign'}
                  </option>
                ))}
              </select>
            </div>
            {loading && <span style={{ color: C.accent, fontSize: 12, paddingBottom: 8 }}>Analyzing...</span>}
          </div>

          {/* Anomaly status banner */}
          {analysis && (
            <Card style={{ marginBottom: 20, borderColor: statusColor, background: anomaly ? 'rgba(248,81,73,0.05)' : 'rgba(63,185,80,0.04)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ width: 12, height: 12, borderRadius: '50%', background: statusColor, boxShadow: `0 0 10px ${statusColor}`, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 18, fontWeight: 700, color: statusColor }}>
                    {anomaly ? 'ANOMALY DETECTED' : 'NORMAL FLIGHT BEHAVIOUR'}
                  </div>
                  <div style={{ fontSize: 12, color: C.muted, marginTop: 2 }}>
                    {anomaly
                      ? `Isolation Forest flagged abnormal flight dynamics during ${analysis.flight_phase} phase.`
                      : `Flight dynamics consistent with normal operation in ${analysis.flight_phase} phase.`}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', letterSpacing: 1 }}>IForest Score</div>
                  <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 20, fontWeight: 700, color: statusColor }}>{score?.toFixed(4) ?? '—'}</div>
                </div>
              </div>
            </Card>
          )}

          {/* Live telemetry KPIs (behaviour only, no RUL/health) */}
          {analysis && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12, marginBottom: 20 }}>
              <Kpi label="Altitude" value={lt.alt_m?.toFixed(0) || '—'} unit="metres" color={C.accent} />
              <Kpi label="Airspeed" value={lt.speed_ms?.toFixed(1) || '—'} unit="m/s" color={C.accent} />
              <Kpi label="Vertical Rate" value={lt.vertical_rate?.toFixed(1) || '—'} unit="m/step" color={C.accent} />
              <Kpi label="Flight Phase" value={(analysis.flight_phase || '—')} color={C.text} />
              <Kpi label="Anomaly Status" value={anomaly ? 'FLAG' : 'OK'} unit={`score ${score?.toFixed(3) ?? '—'}`} color={statusColor} />
            </div>
          )}

          {/* Live airspace map — all aircraft, FlightRadar style */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <Label>Live Airspace — click any aircraft to inspect</Label>
              <span style={{ fontSize: 11, color: C.dim }}>
                Green = tracked fleet · Red = anomaly · Others coloured by altitude
              </span>
            </div>
            <LiveMap
              aircraft={scope === 'pak' ? mapAircraft.filter(a => a.is_pakistani) : mapAircraft}
              selected={sel}
              onSelect={(cs) => setSel(cs)}
              trail={trail}
              height={480}
            />
          </div>

          {/* Diagnostics panels */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Card style={{ flex: 1 }}>
                <Label>Flight-Behaviour Attribution</Label>
                <div style={{ fontSize: 11, color: C.dim, marginBottom: 12 }}>
                  Relative contribution of each live signal to the anomaly assessment.
                </div>
                {analysis?.explainability_shap ? analysis.explainability_shap
                  .filter(it => !/RUL|engine|wear/i.test(it.feature))   // hide engine-wear features here
                  .map((it, i) => {
                    const all = analysis.explainability_shap.filter(x => !/RUL|engine|wear/i.test(x.feature))
                    const max = Math.max(...all.map(x => Math.abs(x.impact)), 0.0001)
                    const col = it.impact < 0 ? C.red : C.green
                    return (
                      <div key={i} style={{ marginBottom: 10 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                          <span style={{ fontSize: 11, color: C.muted }}>{it.feature}</span>
                          <span style={{ fontSize: 11, color: col, fontFamily: 'monospace' }}>{it.impact.toFixed(2)}</span>
                        </div>
                        <Bar value={Math.abs(it.impact)} max={max} color={col} height={5} />
                      </div>
                    )
                  }) : <Empty>{loading ? 'Loading...' : 'No data'}</Empty>}
              </Card>

              {analysis && (
                <Card>
                  <Label>Flight Details</Label>
                  {[
                    ['Callsign', toIATA(sel)],
                    ['Raw ID', sel],
                    ['Phase', analysis.flight_phase || '—'],
                    ['Records Used', analysis.records_used ?? '—'],
                    ['Position', `${lat?.toFixed(2)}, ${lon?.toFixed(2)}`],
                  ].map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: `1px solid ${C.border}`, fontSize: 12 }}>
                      <span style={{ color: C.muted }}>{k}</span>
                      <span style={{ color: C.text, fontFamily: k === 'Callsign' || k === 'Raw ID' ? 'Orbitron, monospace' : 'Inter' }}>{v}</span>
                    </div>
                  ))}
                </Card>
              )}
            </div>
          </div>
        </>
      )}
    </Page>
  )
}