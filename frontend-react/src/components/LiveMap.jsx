import { useState, useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Polyline, Popup, useMap, CircleMarker } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { C } from './ui'

// ── Aircraft icon: a real plane silhouette, rotated to its heading ──
// Visibility is the priority: a dark halo sits behind a bright fill so the
// aircraft reads clearly against both dark and light tiles.
function planeIcon({ heading = 0, color = '#58a6ff', size = 28, selected = false,
                    dark = true, inFleet = false, anomaly = false }) {
  const PATH = 'M12 2 L13.6 9.4 L22 12.2 L22 14 L13.6 12.6 L13.2 19 L15.8 20.6 L15.8 22 L12 21 L8.2 22 L8.2 20.6 L10.8 19 L10.4 12.6 L2 14 L2 12.2 L10.4 9.4 Z'
  const halo = dark ? 'rgba(0,0,0,0.85)' : 'rgba(255,255,255,0.95)'

  // COLOUR always means ALTITUDE — never anything else.
  // Membership and anomaly are shown by RING, not colour, so the two meanings
  // can never be confused with each other.
  //   white ring   -> in our tracked fleet
  //   magenta ring -> anomaly flagged (pulses)
  const ringColor = anomaly ? '#ff2bd1' : inFleet ? '#ffffff' : null
  const ring = ringColor
    ? `<circle cx="12" cy="12" r="11" fill="none" stroke="${ringColor}"
               stroke-width="${anomaly ? 2.2 : 1.6}"
               ${anomaly ? 'stroke-dasharray="3 2"' : ''} opacity="0.95"/>`
    : ''

  const glow = selected
    ? `drop-shadow(0 0 7px ${color}) drop-shadow(0 0 14px ${color})`
    : anomaly
      ? 'drop-shadow(0 0 6px #ff2bd1)'
      : `drop-shadow(0 0 3px ${halo})`

  const svg = `
    <svg viewBox="0 0 24 24" width="${size}" height="${size}"
         style="filter:${glow};">
      <g style="transform: rotate(${heading}deg); transform-origin: 12px 12px;
                transition: transform .45s linear;">
        <path d="${PATH}" fill="none" stroke="${halo}" stroke-width="4" stroke-linejoin="round"/>
        <path d="${PATH}" fill="${color}" stroke="${selected ? '#ffffff' : halo}"
              stroke-width="${selected ? 1.4 : 0.8}" stroke-linejoin="round"/>
      </g>
      ${ring}
    </svg>`

  return L.divIcon({
    html: svg,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

// Colour by altitude — brightened for dark-map legibility
function altColor(alt) {
  if (alt == null) return '#9ba3af'
  if (alt < 2000)  return '#ff6b64'   // low    — bright red
  if (alt < 6000)  return '#ffc233'   // mid    — bright amber
  if (alt < 10000) return '#4ade80'   // high   — bright green
  return '#58a6ff'                    // cruise — bright blue
}

function Recenter({ lat, lon, zoom }) {
  const map = useMap()
  useEffect(() => {
    if (lat != null && lon != null) map.flyTo([lat, lon], zoom ?? map.getZoom(), { duration: 1 })
  }, [lat, lon])
  return null
}

/**
 * FlightRadar-style live map.
 *
 * props:
 *   aircraft   [{hex, callsign, lat, lon, altitude, track, in_fleet, anomaly, ...}]
 *   selected   callsign of the highlighted aircraft (optional)
 *   onSelect   fn(callsign)
 *   trail      [{lat, lon}]  path of the selected aircraft (optional)
 *   height     px
 *   onlyFleet  if true, dim aircraft that aren't in the tracked fleet
 */
export default function LiveMap({
  aircraft = [], selected = null, onSelect = () => {},
  trail = [], height = 460, onlyFleet = false,
}) {
  const [dark, setDark] = useState(true)

  const sel = useMemo(
    () => aircraft.find(a => a.callsign === selected) || null,
    [aircraft, selected]
  )

  const center = sel ? [sel.lat, sel.lon] : [30.3753, 69.3451]  // Pakistan
  const trailPts = trail.filter(p => p.lat && p.lon).map(p => [p.lat, p.lon])

  const tiles = dark
    ? {
        url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        attr: '&copy; OpenStreetMap &copy; CARTO',
      }
    : {
        url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        attr: '&copy; OpenStreetMap &copy; CARTO',
      }

  return (
    <div style={{ position: 'relative', height, borderRadius: 12, overflow: 'hidden',
                  border: `1px solid ${C.border}` }}>

      {/* Controls */}
      <div style={{ position: 'absolute', top: 10, right: 10, zIndex: 1000, display: 'flex', gap: 6 }}>
        <button onClick={() => setDark(d => !d)}
          style={{
            padding: '5px 11px', fontSize: 11, borderRadius: 6, cursor: 'pointer',
            background: 'rgba(13,17,23,.88)', color: C.text,
            border: `1px solid ${C.border}`, backdropFilter: 'blur(6px)',
          }}>
          {dark ? '☀ Light' : '🌙 Dark'}
        </button>
      </div>

      {/* Legend — colour = altitude, ring = what the aircraft IS */}
      <div style={{
        position: 'absolute', bottom: 10, left: 10, zIndex: 1000,
        background: 'rgba(6,8,16,.92)', border: `1px solid ${C.border}`,
        borderRadius: 8, padding: '9px 12px', backdropFilter: 'blur(8px)',
      }}>
        <div style={{ fontSize: 9, color: C.muted, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 4 }}>
          Colour = altitude
        </div>
        {[['#58a6ff', '10 km+'], ['#4ade80', '6–10 km'],
          ['#ffc233', '2–6 km'], ['#ff6b64', 'below 2 km']].map(([col, lbl]) => (
          <div key={lbl} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
            <span style={{ width: 8, height: 8, background: col, borderRadius: 2 }} />
            <span style={{ fontSize: 10, color: C.muted }}>{lbl}</span>
          </div>
        ))}

        <div style={{ fontSize: 9, color: C.muted, letterSpacing: 1, textTransform: 'uppercase',
                      marginTop: 7, paddingTop: 6, borderTop: `1px solid ${C.border}`, marginBottom: 4 }}>
          Ring = aircraft
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', border: '1.6px solid #ffffff' }} />
          <span style={{ fontSize: 10, color: C.text }}>Tracked fleet</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%',
                         border: '2px dashed #ff2bd1', boxShadow: '0 0 5px #ff2bd1' }} />
          <span style={{ fontSize: 10, color: '#ff2bd1' }}>Anomaly flagged</span>
        </div>

        <div style={{ marginTop: 6, paddingTop: 5, borderTop: `1px solid ${C.border}`,
                      fontSize: 10, color: C.text }}>
          {aircraft.length} aircraft · {aircraft.filter(a => a.in_fleet).length} in fleet
        </div>
      </div>

      <MapContainer center={center} zoom={6} style={{ height: '100%', width: '100%', background: '#060810' }}
                    worldCopyJump>
        <TileLayer url={tiles.url} attribution={tiles.attr} />
        {sel && <Recenter lat={sel.lat} lon={sel.lon} zoom={7} />}

        {/* Trail of the selected aircraft */}
        {trailPts.length > 1 && (
          <>
            {/* dark under-stroke so the trail reads on any tile */}
            <Polyline positions={trailPts} color="#000000" weight={6} opacity={0.5} />
            <Polyline positions={trailPts} color="#58a6ff" weight={3} opacity={0.95} />
            <CircleMarker center={trailPts[0]} radius={5}
              pathOptions={{ color: '#ffffff', weight: 2, fillColor: '#58a6ff', fillOpacity: 1 }}>
              <Popup>Track start (earliest recorded position)</Popup>
            </CircleMarker>
          </>
        )}

        {/* Every aircraft */}
        {aircraft.map(a => {
          if (a.lat == null || a.lon == null) return null
          const isSel  = a.callsign === selected
          const dimmed = onlyFleet && !a.in_fleet
          // Colour ALWAYS encodes altitude. Fleet membership and anomaly are
          // shown by a RING, so a green aircraft never means two things at once.
          const color  = altColor(a.altitude)

          return (
            <Marker
              key={a.hex + a.callsign}
              position={[a.lat, a.lon]}
              opacity={dimmed ? 0.3 : 1}
              icon={planeIcon({
                heading: a.track ?? 0,
                color,
                size: isSel ? 38 : a.in_fleet ? 31 : 24,
                selected: isSel,
                dark,
                inFleet: a.in_fleet,
                anomaly: a.anomaly,
              })}
              eventHandlers={{ click: () => onSelect(a.callsign) }}
            >
              <Popup>
                <div style={{ fontFamily: 'system-ui', minWidth: 180 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 3 }}>
                    {a.callsign}
                  </div>
                  {a.tail_number && (
                    <div style={{ fontSize: 12, color: '#3fb950', marginBottom: 4 }}>
                      {a.tail_number} · {a.airline}
                      {a.aircraft_type ? ` · ${a.aircraft_type}` : ''}
                    </div>
                  )}
                  {!a.in_fleet && (
                    <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>
                      {a.is_pakistani ? 'Pakistani carrier' : 'Foreign operator'} — not in tracked fleet
                    </div>
                  )}
                  <table style={{ fontSize: 11, borderCollapse: 'collapse' }}>
                    <tbody>
                      <tr><td style={{ paddingRight: 10, color: '#666' }}>Altitude</td>
                          <td>{a.altitude != null ? `${Math.round(a.altitude)} m` : '—'}</td></tr>
                      <tr><td style={{ paddingRight: 10, color: '#666' }}>Speed</td>
                          <td>{a.velocity != null ? `${a.velocity.toFixed(0)} m/s` : '—'}</td></tr>
                      <tr><td style={{ paddingRight: 10, color: '#666' }}>Heading</td>
                          <td>{a.track != null ? `${Math.round(a.track)}°` : '—'}</td></tr>
                      <tr><td style={{ paddingRight: 10, color: '#666' }}>Vert. rate</td>
                          <td>{a.vertical_rate != null ? `${a.vertical_rate.toFixed(1)} m/s` : '—'}</td></tr>
                    </tbody>
                  </table>
                  {a.anomaly && (
                    <div style={{ marginTop: 5, fontSize: 11, color: '#f85149', fontWeight: 600 }}>
                      ⚠ Anomaly flagged
                    </div>
                  )}
                  <div style={{ marginTop: 5, fontSize: 10, color: '#999' }}>
                    Route not broadcast on ADS-B
                  </div>
                </div>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
    </div>
  )
}