import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Polyline, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { getLiveFleet, analyzeLive, getLiveRoute, healthColor, riskColor, toIATA } from '../api'
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

const planeIcon = L.divIcon({ html: '<div style="font-size:22px">✈</div>', iconSize: [24, 24], iconAnchor: [12, 12], className: '' })

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
        if (!sel) setSel(list[0].tail_number)
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

  const lt     = analysis?.live_telemetry || {}
  const lat    = lt.lat || 30.3753
  const lon    = lt.lon || 69.3451
  const health = analysis?.health_score ?? 0
  const coords = (route?.route_points || []).filter(p => p.lat && p.lon).map(p => [p.lat, p.lon])

  return (
    <Page eyebrow="OpenSky Network — Live ADS-B" title="Live Flight Dashboard"
      subtitle="Real-time tracking of aircraft currently broadcasting over the region"
      right={<Badge color={noLive ? C.yellow : C.green}>{noLive ? 'No live flights' : `${fleet.length} live`}</Badge>}>

      {fleetLoad ? <Spinner text="Connecting to live feed..." /> : noLive ? (
        <Card>
          <Empty>
            No aircraft are currently broadcasting live ADS-B over the region.<br />
            This is normal on the free OpenSky tier — the feed updates as flights pass overhead.<br />
            <span style={{ color: C.muted }}>For continuous fleet tracking, use the Pakistan Fleet page.</span>
          </Empty>
        </Card>
      ) : (
        <>
          {/* Selector */}
          <div style={{ marginBottom: 20 }}>
            <Label>Select Live Flight</Label>
            <select value={sel} onChange={e => setSel(e.target.value)}
              style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text,
                       padding: '8px 14px', borderRadius: 8, fontSize: 13, minWidth: 260, cursor: 'pointer' }}>
              {fleet.map(f => <option key={f.tail_number} value={f.tail_number}>{toIATA(f.tail_number)} ({f.tail_number})</option>)}
            </select>
            {loading && <span style={{ color: C.accent, fontSize: 12, marginLeft: 12 }}>Analyzing...</span>}
          </div>

          {/* KPIs */}
          {analysis && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12, marginBottom: 20 }}>
              <Kpi label="Predicted RUL" value={analysis.predicted_rul_cycles} unit="cycles" color={C.accent} />
              <Kpi label="Health Score" value={Math.round(health)} unit="/ 100" color={healthColor(health)} />
              <Kpi label="Risk Level" value={analysis.risk_level} color={riskColor(analysis.risk_level)} />
              <Kpi label="Altitude" value={lt.alt_m?.toFixed(0) || '—'} unit="metres" />
              <Kpi label="Airspeed" value={lt.speed_ms?.toFixed(1) || '—'} unit="m/s" />
            </div>
          )}

          {/* Map + diagnostics */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Card style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}` }}><Label>Live Position & Track</Label></div>
              <div style={{ height: 380 }}>
                <MapContainer center={[lat, lon]} zoom={5} style={{ height: '100%', width: '100%' }}>
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  <FlyTo lat={lat} lon={lon} />
                  {coords.length > 1 && <Polyline positions={coords} color={C.accent} weight={2} dashArray="6 4" />}
                  <Marker position={[lat, lon]} icon={planeIcon}>
                    <Popup><b>{toIATA(sel)}</b><br />{lt.alt_m?.toFixed(0)}m · {lt.speed_ms?.toFixed(1)} m/s</Popup>
                  </Marker>
                </MapContainer>
              </div>
            </Card>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Card style={{ flex: 1 }}>
                <Label>ML Diagnostics — Feature Attribution</Label>
                {analysis?.explainability_shap ? analysis.explainability_shap.map((it, i) => {
                  const max = Math.max(...analysis.explainability_shap.map(x => Math.abs(x.impact)))
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
                  <Label>Emissions & Anomaly</Label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                    <div><div style={{ fontSize: 10, color: C.dim }}>FUEL</div><div style={{ fontFamily: 'Orbitron', fontSize: 18, color: C.text }}>{(analysis.route_and_emissions?.predicted_fuel_liters || 0).toLocaleString()}</div><div style={{ fontSize: 10, color: C.dim }}>litres</div></div>
                    <div><div style={{ fontSize: 10, color: C.dim }}>CO₂</div><div style={{ fontFamily: 'Orbitron', fontSize: 18, color: C.text }}>{(analysis.route_and_emissions?.predicted_co2_kg || 0).toLocaleString()}</div><div style={{ fontSize: 10, color: C.dim }}>kg</div></div>
                    <div><div style={{ fontSize: 10, color: C.dim }}>ADS-B</div><div style={{ fontFamily: 'Orbitron', fontSize: 18, color: analysis.anomaly_flag ? C.red : C.green }}>{analysis.anomaly_flag ? 'FLAG' : 'OK'}</div><div style={{ fontSize: 10, color: C.dim }}>{analysis.iforest_score}</div></div>
                  </div>
                </Card>
              )}
            </div>
          </div>
        </>
      )}
    </Page>
  )
}
