import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Polyline, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { getLiveFleet, analyzeLive, getLiveRoute, toIATA } from '../api'
import { Page, Card, Label, Kpi, Badge, Bar, Empty, Spinner, C } from '../components/ui'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl:       'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl:     'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

function FlyTo({ lat, lon }) {
  const map = useMap()
  useEffect(() => { if (lat && lon) map.flyTo([lat, lon], 6, { duration: 1.2 }) }, [lat, lon])
  return null
}

const planeIcon = (color) => L.divIcon({
  html: `<div style="font-size:22px;line-height:1;filter:drop-shadow(0 0 4px ${color})">✈</div>`,
  iconSize: [24, 24], iconAnchor: [12, 12], className: '',
})

export default function Dashboard() {
  const [fleet, setFleet]       = useState([])
  const [sel, setSel]           = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [route, setRoute]       = useState(null)
  const [loading, setLoading]   = useState(false)
  const [fleetLoad, setFleetLoad] = useState(true)
  const [noLive, setNoLive]     = useState(false)

  useEffect(() => {
    const load = () => getLiveFleet().then(r => {
      const list = r.data.fleet || []
      if (list.length && list[0].tail_number !== 'No live flights' && list[0].tail_number !== 'Error') {
        setFleet(list); setNoLive(false)
        setSel(prev => prev || list[0].tail_number)
      } else {
        setFleet([]); setNoLive(true)
      }
    }).catch(() => setNoLive(true)).finally(() => setFleetLoad(false))
    load()
    const iv = setInterval(load, 30000)
    return () => clearInterval(iv)
  }, [])

  useEffect(() => {
    if (!sel) return
    setLoading(true); setAnalysis(null); setRoute(null)
    Promise.all([
      analyzeLive(sel).catch(() => ({ data: null })),
      getLiveRoute(sel).catch(() => ({ data: null })),
    ]).then(([a, r]) => { setAnalysis(a.data); setRoute(r.data) })
      .finally(() => setLoading(false))
  }, [sel])

  const lt      = analysis?.live_telemetry || {}
  const lat     = lt.lat || 30.3753
  const lon     = lt.lon || 69.3451
  const anomaly = analysis?.anomaly_flag === 1
  const score   = analysis?.iforest_score
  const statusColor = anomaly ? C.red : C.green
  const coords  = (route?.route_points || []).filter(p => p.lat && p.lon).map(p => [p.lat, p.lon])

  return (
    <Page eyebrow="OpenSky Network — Real-Time ADS-B" title="Live Anomaly Monitor"
      subtitle="Real-time flight-behaviour monitoring and anomaly detection over the region"
      right={<Badge color={noLive ? C.yellow : C.green}>{noLive ? 'No live flights' : `${fleet.length} live`}</Badge>}>

      {/* Scope note — sets expectations honestly */}
      <div style={{ background: 'rgba(56,139,253,0.06)', border: `1px solid ${C.border}`, borderRadius: 10, padding: '12px 16px', marginBottom: 20, fontSize: 12, color: C.muted, lineHeight: 1.6 }}>
        This monitor tracks <strong style={{ color: C.text }}>live aircraft broadcasting ADS-B</strong> over the region via the OpenSky Network and runs each through the Isolation Forest model to flag abnormal flight behaviour in real time.
        Engine Remaining-Useful-Life prediction is not shown here — RUL depends on accumulated engine cycles, which are only available for the 44 curated aircraft on the <strong style={{ color: C.accent }}>Pakistan Fleet</strong> page.
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
          <div style={{ marginBottom: 20 }}>
            <Label>Select Live Flight</Label>
            <select value={sel} onChange={e => setSel(e.target.value)}
              style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text,
                       padding: '8px 14px', borderRadius: 8, fontSize: 13, minWidth: 280, cursor: 'pointer' }}>
              {fleet.map(f => <option key={f.tail_number} value={f.tail_number}>{toIATA(f.tail_number)} ({f.tail_number})</option>)}
            </select>
            {loading && <span style={{ color: C.accent, fontSize: 12, marginLeft: 12 }}>Analyzing...</span>}
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

          {/* Map + flight-behaviour attribution */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Card style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}` }}><Label>Live Position & Track</Label></div>
              <div style={{ height: 380 }}>
                <MapContainer center={[lat, lon]} zoom={5} style={{ height: '100%', width: '100%' }}>
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  <FlyTo lat={lat} lon={lon} />
                  {coords.length > 1 && <Polyline positions={coords} color={statusColor} weight={2} dashArray="6 4" />}
                  <Marker position={[lat, lon]} icon={planeIcon(statusColor)}>
                    <Popup><b>{toIATA(sel)}</b><br />{lt.alt_m?.toFixed(0)}m · {lt.speed_ms?.toFixed(1)} m/s</Popup>
                  </Marker>
                </MapContainer>
              </div>
            </Card>

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