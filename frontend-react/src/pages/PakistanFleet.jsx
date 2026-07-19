import { useState, useEffect } from 'react'
import LiveMap from '../components/LiveMap'
import { useLocation } from 'react-router-dom'
import { getPakFleet, analyzePak, getLiveTrack, toIATA, AIRLINE_ALIAS } from '../api'

const hCol = s => s >= 70 ? '#3fb950' : s >= 40 ? '#d29922' : '#f85149'

const ALIAS = {
  'PIA':'PIA','Pakistan International Airlines':'PIA',
  'AirBlue':'AirBlue','AirSial':'AirSial',
  'FlyJinnah':'FlyJinnah','Fly Jinnah':'FlyJinnah',
}

const Card = ({children, style={}}) => (
  <div style={{background:'#0d1117',border:'1px solid #21262d',borderRadius:10,padding:'16px 20px',...style}}>
    {children}
  </div>
)

const Lbl = ({children}) => (
  <div style={{fontSize:10,fontWeight:600,letterSpacing:2,textTransform:'uppercase',color:'#7d8590',marginBottom:8}}>
    {children}
  </div>
)

// Per-aircraft seed for consistent variation (not random each render)
export default function PakistanFleet() {
  const location = useLocation()
  const [fleet,      setFleet]      = useState([])
  const [airlines,   setAirlines]   = useState([])
  const [airline,    setAirline]    = useState('')
  const [tail,       setTail]       = useState('')
  const [analysis,   setAnalysis]   = useState(null)
  const [trail,      setTrail]      = useState([])
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState('')

  useEffect(() => {
    getPakFleet().then(r => {
      const data = r.data.fleet || []
      setFleet(data)
      const als = [...new Set(data.map(p=>p.airline).filter(Boolean))]
      setAirlines(als)
      // Airline from router state. Home passes a canonical key
      // ('PIA','AirBlue','AirSial','FlyJinnah'); match against DB values via ALIAS.
      const fromState = location.state?.airline
      let initial = als[0]
      if (fromState) {
        const matched = als.find(a => (ALIAS[a] || a) === fromState || a === fromState)
        if (matched) initial = matched
      }

      // If a specific aircraft was requested (e.g. clicking an airborne card on
      // Home), open it directly instead of making the user pick again.
      const wantTail = location.state?.tail
      const plane = wantTail && data.find(p => p.tail_number === wantTail)
      if (plane) {
        initial = plane.airline           // make sure the airline matches the aircraft
        setAirline(initial)
        setTail(plane.tail_number)        // auto-select it
        return
      }

      if (initial) setAirline(initial)
    }).catch(() => setError('Cannot connect to backend. Is uvicorn running?'))
  }, [location.state])

  // NOTE: clearing the aircraft when the airline changes is handled directly in
  // the airline button's onClick, not in an effect. Doing it in an effect would
  // also fire when the airline is set programmatically (e.g. when Home asks for
  // a specific aircraft), wiping the very aircraft we were told to open.

  useEffect(() => {
    if (!tail) return
    setLoading(true); setError(''); setAnalysis(null); setTrail([])

    // The trail endpoint keys on CALLSIGN (the live flight), not the
    // registration. Look up this aircraft's current callsign from the fleet
    // list; if it's grounded there is no callsign and no trail to fetch.
    const plane = fleet.find(p => p.tail_number === tail)
    const cs = plane?.status === 'airborne'
      ? (plane.current_flight || plane.callsign)
      : null

    Promise.all([
      analyzePak(tail).catch(e => ({ data: null, error: e.response?.status })),
      cs ? getLiveTrack(cs).catch(() => ({ data: { points: [] } }))
         : Promise.resolve({ data: { points: [] } }),
    ])
      .then(([a, t]) => {
        if (a.data) setAnalysis(a.data)
        setTrail(t.data?.points || [])
        if (!a.data) setError(`No analysis available for ${tail} yet.`)
      })
      .catch(e => setError(`Failed to load ${tail}: ${e.message}`))
      .finally(() => setLoading(false))
  }, [tail, fleet])

  const planes   = fleet.filter(p => p.airline === airline)
  const selPlane = fleet.find(p => p.tail_number === tail) || {}
  const isAirborne = selPlane.status === 'airborne'
  const flightNo = selPlane.current_flight || selPlane.callsign
  const lt       = analysis?.live_telemetry || {}
  const lat      = lt.lat  || 30.3753
  const lon      = lt.lon  || 69.3451
  const health   = analysis?.health_score || 50
  const rul      = analysis?.predicted_rul_cycles || '—'
  const risk     = analysis?.risk_level || '—'
  const isEst    = analysis?.anomaly_flag === 1

  return (
    <div style={{padding:'28px 36px', maxWidth:1500, margin:'0 auto'}}>

      {/* Header */}
      <div style={{marginBottom:20}}>
        <div style={{fontSize:10,color:'#484f58',letterSpacing:3,textTransform:'uppercase',marginBottom:4}}>
          Pakistan Fleet — Digital Twin
        </div>
        <div style={{display:'flex',alignItems:'center',gap:12,flexWrap:'wrap'}}>
          <div style={{fontFamily:'Orbitron, monospace',fontSize:26,fontWeight:900,color:'#e6edf3'}}>{tail||'—'}</div>
          {analysis && (
            <span style={{fontSize:13,color:'#7d8590'}}>
              {analysis.aircraft_type} · {ALIAS[analysis.airline]||analysis.airline}
            </span>
          )}
          {tail && (
            <span style={{
              fontSize:11, padding:'3px 10px', borderRadius:20, fontWeight:600,
              display:'inline-flex', alignItems:'center', gap:5,
              background: isAirborne ? 'rgba(63,185,80,0.12)' : 'rgba(125,133,144,0.12)',
              color: isAirborne ? '#3fb950' : '#7d8590',
              border: `1px solid ${isAirborne ? '#3fb95055' : '#7d859033'}`,
            }}>
              <span style={{
                width:6, height:6, borderRadius:'50%',
                background: isAirborne ? '#3fb950' : '#7d8590',
                boxShadow: isAirborne ? '0 0 6px #3fb950' : 'none',
              }}/>
              {isAirborne ? 'AIRBORNE' : 'GROUNDED'}
            </span>
          )}
          {tail && isAirborne && flightNo && (
            <span style={{
              fontSize:12, padding:'3px 10px', borderRadius:20,
              background:'rgba(56,139,253,0.12)', color:'#388bfd',
              border:'1px solid #388bfd55', fontFamily:'Orbitron, monospace', fontWeight:600,
            }}>
              ✈ {toIATA(flightNo)}
            </span>
          )}
          {loading && <span style={{fontSize:12,color:'#388bfd',marginLeft:8}}>Loading...</span>}
        </div>
      </div>

      {error && (
        <div style={{background:'rgba(56,139,253,0.06)',border:'1px solid #21262d',borderRadius:8,padding:'10px 16px',marginBottom:16,fontSize:12,color:'#7d8590'}}>
          ℹ {error}
        </div>
      )}

      {/* Airline + aircraft selectors */}
      <div style={{display:'flex',gap:10,marginBottom:20,flexWrap:'wrap',alignItems:'center'}}>
        {airlines.map(a => (
          <button key={a} onClick={()=>{ setAirline(a); setTail(''); setAnalysis(null); setTrail([]) }}
            style={{
              padding:'6px 16px', borderRadius:20, fontSize:12, cursor:'pointer',
              border: airline===a ? '1px solid #388bfd' : '1px solid #21262d',
              background: airline===a ? 'rgba(56,139,253,0.15)' : 'transparent',
              color: airline===a ? '#388bfd' : '#7d8590',
            }}>
            {ALIAS[a]||a}
          </button>
        ))}
        <select value={tail} onChange={e=>setTail(e.target.value)}
          style={{
            background:'#0d1117', border: tail ? '1px solid #21262d' : '1px solid #388bfd', color: tail ? '#e6edf3' : '#388bfd',
            padding:'6px 14px', borderRadius:8, fontSize:12, cursor:'pointer', minWidth:240,
          }}>
          <option value="">— Select an aircraft —</option>
          {planes.map(p => (
            <option key={p.tail_number} value={p.tail_number}>
              {p.tail_number} — {p.aircraft_type?.split('-')[0]||''}
              {p.status==='airborne'
                ? ` ✈ ${toIATA(p.current_flight||p.callsign||'')}`
                : ' 🅿'}
            </option>
          ))}
        </select>
      </div>

      {/* Prompt when an airline is selected but no aircraft yet */}
      {!tail && !error && (
        <div style={{
          background:'#0d1117', border:'1px dashed #21262d', borderRadius:12,
          padding:'48px 24px', textAlign:'center', marginTop:8,
        }}>
          <div style={{ fontSize:32, marginBottom:12 }}>✈</div>
          <div style={{ fontFamily:'Orbitron, monospace', fontSize:16, color:'#e6edf3', marginBottom:6 }}>
            {ALIAS[airline]||airline} selected
          </div>
          <div style={{ fontSize:13, color:'#7d8590' }}>
            Choose an aircraft from the dropdown above to view its digital twin analysis.
          </div>
        </div>
      )}

      {/* KPIs */}
      {tail && (
      <div style={{display:'grid',gridTemplateColumns:'repeat(5,1fr)',gap:12,marginBottom:20}}>
        {[
          {label:'Predicted RUL', value:rul,                          unit:'cycles',  color:'#388bfd'},
          {label:'Health Score',  value:analysis ? Math.round(health) : '—', unit:'/ 100', color:hCol(health)},
          {label:'Risk Level',    value:risk,                         unit:'',        color:hCol(health)},
          {label:'Altitude',      value:lt.alt_m ? lt.alt_m.toFixed(0) : '—', unit:'m', color:'#e6edf3'},
          {label:'Airspeed',      value:lt.speed_ms ? lt.speed_ms.toFixed(1) : '—', unit:'m/s', color:'#e6edf3'},
        ].map(({label,value,unit,color})=>(
          <Card key={label}>
            <Lbl>{label}</Lbl>
            <div style={{fontFamily:'Orbitron, monospace',fontSize:24,fontWeight:700,color}}>{value}</div>
            {unit && <div style={{fontSize:11,color:'#484f58',marginTop:4}}>{unit}</div>}
          </Card>
        ))}
      </div>
      )}

      {/* Maintenance advisory */}
      {analysis && (risk==='High' || health < 30) && (
        <div style={{
          background:'rgba(248,81,73,0.08)',border:'1px solid #f85149',
          borderRadius:8,padding:'12px 20px',marginBottom:20,
          display:'flex',alignItems:'center',gap:10
        }}>
          <div style={{width:8,height:8,borderRadius:'50%',background:'#f85149',flexShrink:0}}/>
          <span style={{fontSize:13,color:'#f85149'}}>
            Maintenance Advisory — {tail} · RUL: {rul} cycles · Health: {Math.round(health)}/100 · Recommend inspection before next flight.
          </span>
        </div>
      )}

      {/* Map + diagnostics */}
      {tail && (
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:16,marginBottom:20}}>

        {/* Map — only meaningful when the aircraft is actually flying */}
        <Card style={{padding:0,overflow:'hidden'}}>
          <div style={{padding:'12px 16px',borderBottom:'1px solid #21262d'}}>
            <Lbl>{isAirborne ? 'Live Position & Track' : 'Position'}</Lbl>
          </div>
          {isAirborne && selPlane.latitude != null ? (
            <LiveMap
              aircraft={[{
                hex: selPlane.hex_code, callsign: flightNo || tail,
                lat: selPlane.latitude, lon: selPlane.longitude,
                altitude: selPlane.altitude, velocity: selPlane.velocity,
                track: selPlane.track ?? 0, in_fleet: true, anomaly: analysis?.anomaly_flag === 1,
                tail_number: tail, airline: ALIAS[selPlane.airline]||selPlane.airline,
                aircraft_type: selPlane.aircraft_type, is_pakistani: true,
              }]}
              selected={flightNo || tail}
              trail={trail}
              height={360}
            />
          ) : (
            <div style={{height:360,display:'flex',flexDirection:'column',alignItems:'center',
                         justifyContent:'center',gap:8,color:'#484f58'}}>
              <div style={{fontSize:34}}>🅿</div>
              <div style={{fontSize:14,color:'#7d8590'}}>Aircraft is on the ground</div>
              <div style={{fontSize:12,textAlign:'center',maxWidth:280,lineHeight:1.5}}>
                No live position is broadcast while parked. The map appears when
                this aircraft is airborne and transmitting ADS-B.
              </div>
            </div>
          )}
        </Card>

        {/* Right column */}
        <div style={{display:'flex',flexDirection:'column',gap:12}}>

          {/* Diagnostics — split honestly by whether the aircraft is flying */}
          <Card style={{flex:1}}>
            <Lbl>
              {isAirborne ? 'ML Diagnostics — Feature Attribution' : 'Engine Health Diagnostics'}
            </Lbl>

            {!isAirborne && (
              <div style={{fontSize:11,color:'#7d8590',marginBottom:12,lineHeight:1.6,
                           background:'rgba(56,139,253,0.05)',border:'1px solid #21262d',
                           borderRadius:6,padding:'8px 10px'}}>
                This aircraft is grounded, so there is no live telemetry to analyse.
                Anomaly detection and flight-phase attribution require an active flight.
                The figures below come from the engine-wear model, which is based on
                accumulated cycles and is valid whether or not the aircraft is flying.
              </div>
            )}

            {analysis?.explainability_shap ? (
              analysis.explainability_shap
                // On the ground, hide the live-telemetry features — showing an
                // "ADS-B anomaly score" for a parked aircraft would be dishonest.
                .filter(item => isAirborne || /RUL|wear|engine|cycle/i.test(item.feature))
                .map((item,i,arr)=>{
                  const max = Math.max(...arr.map(x=>Math.abs(x.impact)), 0.0001)
                  const pct = (Math.abs(item.impact)/max)*100
                  const col = item.impact < 0 ? '#f85149' : '#3fb950'
                  return (
                    <div key={i} style={{marginBottom:10}}>
                      <div style={{display:'flex',justifyContent:'space-between',marginBottom:3}}>
                        <span style={{fontSize:11,color:'#7d8590'}}>{item.feature}</span>
                        <span style={{fontSize:11,color:col,fontFamily:'monospace'}}>{item.impact.toFixed(2)}</span>
                      </div>
                      <div style={{height:5,background:'#21262d',borderRadius:3}}>
                        <div style={{height:'100%',width:`${pct}%`,background:col,borderRadius:3}}/>
                      </div>
                    </div>
                  )
                })
            ) : (
              <div style={{fontSize:12,color:'#484f58'}}>{loading ? 'Loading...' : 'No data'}</div>
            )}
          </Card>

          {/* Info */}
          <Card>
            <Lbl>Aircraft Info</Lbl>
            {[
              ['Registration', tail],
              ['Type',         selPlane.aircraft_type || analysis?.aircraft_type || '—'],
              ['Airline',      ALIAS[selPlane.airline] || selPlane.airline || '—'],
              ['Status',       isAirborne ? 'Airborne' : 'Grounded'],
              // Flight number comes from fleet_status (hex-reconciled), not from
              // the analysis payload — a grounded aircraft has no flight number.
              ['Flight No.',   isAirborne && flightNo ? toIATA(flightNo) : '—'],
              ['Flight Phase', isAirborne ? (analysis?.flight_phase||'—').replace(/_/g,' ') : '—'],
              ['ADS-B Score',  isAirborne ? (analysis?.iforest_score?.toFixed(4) ?? '—') : '—'],
              ['Hex Code',     selPlane.hex_code || '—'],
            ].map(([k,v])=>(
              <div key={k} style={{display:'flex',justifyContent:'space-between',padding:'5px 0',
                                   borderBottom:'1px solid #21262d',fontSize:12}}>
                <span style={{color:'#7d8590'}}>{k}</span>
                <span style={{
                  color: v === '—' ? '#484f58' : '#e6edf3',
                  fontFamily: ['Registration','Flight No.','Hex Code'].includes(k) ? 'Orbitron, monospace' : 'Inter',
                }}>{v}</span>
              </div>
            ))}
          </Card>
        </div>
      </div>
      )}

      {/* Emissions strip — in-flight quantities only */}
      {analysis && (() => {
        const em   = analysis.route_and_emissions || {}
        const fuel = em.predicted_fuel_liters
        const co2  = em.predicted_co2_kg
        // Fuel burn and CO2 are IN-FLIGHT measures. The backend returns null
        // for a grounded aircraft because it is burning nothing — showing "0"
        // would imply we measured zero, and showing a number would be false.
        const groundNote = 'on ground — not burning fuel'
        return (
          <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12}}>
            {[
              {label:'Est. Fuel Burn',
               value: fuel != null ? fuel.toLocaleString() : '—',
               unit:  fuel != null ? 'litres' : groundNote},
              {label:'Est. CO₂',
               value: co2 != null ? co2.toLocaleString() : '—',
               unit:  co2 != null ? 'kg' : groundNote},
              {label:'ADS-B Anomaly',
               value: isAirborne ? (analysis.anomaly_flag ? '⚠ Flagged' : '✓ Normal') : '—',
               unit:  isAirborne
                        ? `score: ${analysis.iforest_score?.toFixed(4) ?? '—'}`
                        : 'no live telemetry to score'},
            ].map(({label,value,unit})=>(
              <Card key={label}>
                <Lbl>{label}</Lbl>
                <div style={{fontFamily:'Orbitron, monospace',fontSize:20,fontWeight:700,
                             color: value === '—' ? '#484f58' : '#e6edf3'}}>{value}</div>
                <div style={{fontSize:11,color:'#484f58',marginTop:4}}>{unit}</div>
              </Card>
            ))}
          </div>
        )
      })()}
    </div>
  )
}