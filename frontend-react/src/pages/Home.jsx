import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPakFleet, analyzePak, getFleetStatus, getWeather, AIRLINE_ALIAS } from '../api'

const Card = ({ children, style = {}, onClick, onMouseEnter, onMouseLeave }) => (
  <div onClick={onClick} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave}
    style={{ background: '#0d1117', border: '1px solid #21262d', borderRadius: 12, padding: '20px 24px', ...style }}>
    {children}
  </div>
)

const Label = ({ children }) => (
  <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: 2, textTransform: 'uppercase', color: '#7d8590', marginBottom: 8 }}>
    {children}
  </div>
)

// Canonical airline buckets. We match DB values via AIRLINE_ALIAS so both
// "PIA" and "Pakistan International Airlines" map to the same bucket.
const AIRLINE_KEYS = ['PIA', 'AirBlue', 'AirSial', 'FlyJinnah']

export default function Home() {
  const navigate = useNavigate()
  const [fleet, setFleet]     = useState([])
  const [health, setHealth]   = useState({})   // tail -> health_score (real, from pak_analyze)
  const [status, setStatus]   = useState({})
  const [weather, setWeather] = useState([])
  const [loading, setLoading] = useState(true)
  const [scanPct, setScanPct] = useState(0)
  const [time, setTime]       = useState(new Date())

  // Load fleet + status + weather first (fast)
  useEffect(() => {
    Promise.all([getPakFleet(), getFleetStatus(), getWeather()])
      .then(([f, s, w]) => {
        setFleet(f.data.fleet || [])
        setStatus(s.data || {})
        setWeather(w.data.weather || [])
      })
      .catch(e => console.error(e))
      .finally(() => setLoading(false))
    const clock = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(clock)
  }, [])

  // Then scan each aircraft for its REAL health (background, progressive)
  useEffect(() => {
    if (!fleet.length) return
    let cancelled = false
    ;(async () => {
      const acc = {}
      for (let i = 0; i < fleet.length; i++) {
        if (cancelled) return
        try {
          const r = await analyzePak(fleet[i].tail_number)
          acc[fleet[i].tail_number] = r.data.health_score
          setHealth({ ...acc })
        } catch { /* skip */ }
        setScanPct(Math.round(((i + 1) / fleet.length) * 100))
      }
    })()
    return () => { cancelled = true }
  }, [fleet])

  // Helper: real health for a plane if scanned, else null
  const planeHealth = (tail) => (tail in health ? health[tail] : null)

  const scannedScores = Object.values(health)
  const fleetHealth = scannedScores.length
    ? Math.round(scannedScores.reduce((a, b) => a + b, 0) / scannedScores.length)
    : null

  const airborne = status.summary?.airborne || 0
  const grounded = status.summary?.grounded || 0
  const critical = Object.entries(health).filter(([, h]) => h < 40).length

  const healthCol = !fleetHealth ? '#388bfd' : fleetHealth >= 70 ? '#3fb950' : fleetHealth >= 40 ? '#d29922' : '#f85149'

  // Per-airline stats using REAL scanned health
  const airlineStats = AIRLINE_KEYS.map(key => {
    const planes = fleet.filter(p => (AIRLINE_ALIAS[p.airline] || p.airline) === key)
    const scores = planes.map(p => planeHealth(p.tail_number)).filter(v => v != null)
    const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null
    return { key, count: planes.length, avg }
  })

  if (loading) return <div style={{ padding: '32px 40px', color: '#7d8590', fontSize: 13 }}>Loading fleet data...</div>

  const scanning = scanPct < 100

  return (
    <div style={{ padding: '32px 40px', maxWidth: 1400, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:32 }}>
        <div>
          <div style={{ fontSize:10, color:'#484f58', letterSpacing:3, textTransform:'uppercase', marginBottom:4 }}>Pakistan Digital Fleet</div>
          <div style={{ fontFamily:'Orbitron, monospace', fontSize:28, fontWeight:900, color:'#e6edf3' }}>Fleet Command Center</div>
        </div>
        <div style={{ textAlign:'right' }}>
          <div style={{ fontFamily:'Orbitron, monospace', fontSize:20, fontWeight:700, color:'#388bfd' }}>
            {time.toLocaleTimeString('en-PK',{timeZone:'Asia/Karachi',hour12:false})}
          </div>
          <div style={{ fontSize:11, color:'#7d8590', marginTop:2 }}>
            PKT · {scanning ? `Analyzing fleet ${scanPct}%` : 'Live'}
          </div>
        </div>
      </div>

      {/* Fleet Health Hero */}
      <Card style={{ marginBottom:24, borderColor:healthCol, position:'relative', overflow:'hidden' }}>
        <div style={{ position:'absolute', top:0, left:0, right:0, height:3, background:`linear-gradient(90deg,${healthCol},transparent)` }} />
        <div style={{ display:'flex', alignItems:'center', gap:48, flexWrap:'wrap' }}>
          <div>
            <Label>Fleet Health Index</Label>
            <div style={{ fontFamily:'Orbitron, monospace', fontSize:72, fontWeight:900, color:healthCol, lineHeight:1 }}>
              {fleetHealth ?? '··'}
            </div>
            <div style={{ fontSize:13, color:'#7d8590', marginTop:8 }}>
              {scanning
                ? `Computing live — ${scannedScores.length}/${fleet.length} aircraft analyzed`
                : `Weighted average across ${scannedScores.length} aircraft`}
            </div>
          </div>
          <div style={{ flex:1, minWidth:200 }}>
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6, fontSize:11, color:'#7d8590' }}>
              <span>Critical</span><span>Moderate</span><span>Healthy</span>
            </div>
            <div style={{ height:12, background:'#21262d', borderRadius:6, overflow:'hidden' }}>
              <div style={{ height:'100%', width:`${fleetHealth??0}%`, background:'linear-gradient(90deg,#f85149,#d29922,#3fb950)', borderRadius:6, transition:'width 1s ease' }} />
            </div>
            <div style={{ display:'flex', justifyContent:'space-between', marginTop:6, fontSize:11, color:'#7d8590' }}>
              <span>0</span><span>50</span><span>100</span>
            </div>
          </div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, minWidth:220 }}>
            {[
              {label:'Total Aircraft', value:fleet.length, color:'#388bfd'},
              {label:'Airborne Now',   value:airborne,     color:'#3fb950'},
              {label:'Grounded',       value:grounded,     color:'#7d8590'},
              {label:'Critical',       value:scanning ? '··' : critical, color:critical>0?'#f85149':'#3fb950'},
            ].map(({label,value,color})=>(
              <div key={label} style={{ background:'#161b22', borderRadius:8, padding:'10px 14px', border:'1px solid #21262d' }}>
                <div style={{ fontSize:9, color:'#7d8590', letterSpacing:1, textTransform:'uppercase' }}>{label}</div>
                <div style={{ fontFamily:'Orbitron, monospace', fontSize:22, fontWeight:700, color }}>{value}</div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Airline breakdown */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16, marginBottom:24 }}>
        {airlineStats.map(({key,count,avg})=>{
          const col = avg == null ? '#388bfd' : avg>=70?'#3fb950':avg>=40?'#d29922':'#f85149'
          return (
            <Card key={key} style={{ cursor:'pointer' }}
              onClick={()=>navigate('/pakistan', { state: { airline: key } })}
              onMouseEnter={e=>e.currentTarget.style.borderColor='#388bfd'}
              onMouseLeave={e=>e.currentTarget.style.borderColor='#21262d'}>
              <div style={{ fontSize:11, color:'#7d8590', marginBottom:4 }}>{key}</div>
              <div style={{ fontFamily:'Orbitron, monospace', fontSize:32, fontWeight:700, color:col }}>{avg ?? '··'}</div>
              <div style={{ fontSize:11, color:'#484f58', marginTop:4 }}>health · {count} aircraft</div>
              <div style={{ marginTop:12, height:4, background:'#21262d', borderRadius:2 }}>
                <div style={{ height:'100%', width:`${avg??0}%`, background:col, borderRadius:2, transition:'width 0.6s' }} />
              </div>
            </Card>
          )
        })}
      </div>

      {/* Weather + Quick access */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16, marginBottom:24 }}>
        <Card>
          <Label>Live Airport Weather</Label>
          {weather.length===0
            ? <div style={{ fontSize:12, color:'#484f58' }}>Waiting for pipeline cycle...</div>
            : <div style={{ display:'grid', gridTemplateColumns:'repeat(2,1fr)', gap:12 }}>
                {weather.map(w=>(
                  <div key={w.iata} style={{ background:'#161b22', borderRadius:8, padding:'10px 14px', border:'1px solid #21262d' }}>
                    <div style={{ display:'flex', justifyContent:'space-between' }}>
                      <div style={{ fontFamily:'Orbitron, monospace', fontSize:14, color:'#388bfd' }}>{w.iata}</div>
                      <div style={{ fontSize:11, color:'#7d8590' }}>{w.conditions}</div>
                    </div>
                    <div style={{ fontSize:20, fontWeight:500, color:'#e6edf3', marginTop:4 }}>{Math.round(w.temp_c)}°C</div>
                    <div style={{ fontSize:11, color:'#7d8590' }}>Wind {Math.round(w.wind_ms)} m/s</div>
                  </div>
                ))}
              </div>
          }
        </Card>
        <Card>
          <Label>Quick Access</Label>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10 }}>
            {[
              {label:'Pakistan Fleet',   path:'/pakistan',    icon:'🇵🇰', desc:'Live aircraft tracking'},
              {label:'Maintenance',      path:'/maintenance', icon:'🔧',  desc:'Log & track service'},
              {label:'Fleet Overview',   path:'/fleet',       icon:'✈',   desc:'All 44 aircraft'},
              {label:'Flight Simulator', path:'/simulator',   icon:'🧮',  desc:'What-if analysis'},
              {label:'CO₂ Dashboard',    path:'/co2',         icon:'🌿',  desc:'ESG reporting'},
              {label:'Route Analyzer',   path:'/route',       icon:'🗺',  desc:'Efficiency optimizer'},
            ].map(({label,path,icon,desc})=>(
              <div key={path} onClick={()=>navigate(path)}
                style={{ background:'#161b22', border:'1px solid #21262d', borderRadius:8, padding:'12px 14px', cursor:'pointer' }}
                onMouseEnter={e=>e.currentTarget.style.borderColor='#388bfd'}
                onMouseLeave={e=>e.currentTarget.style.borderColor='#21262d'}>
                <div style={{ fontSize:18, marginBottom:4 }}>{icon}</div>
                <div style={{ fontSize:12, fontWeight:500, color:'#e6edf3' }}>{label}</div>
                <div style={{ fontSize:10, color:'#484f58', marginTop:2 }}>{desc}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Critical alert */}
      {!scanning && critical>0 && (
        <Card style={{ borderColor:'#f85149' }}>
          <Label>Critical Aircraft Requiring Attention</Label>
          <div style={{ display:'flex', gap:10, flexWrap:'wrap', marginTop:8 }}>
            {Object.entries(health).filter(([,h])=>h<40).map(([tail])=>(
              <div key={tail} onClick={()=>navigate('/maintenance')}
                style={{ background:'rgba(248,81,73,0.1)', border:'1px solid #f85149', borderRadius:8, padding:'8px 16px', cursor:'pointer', fontSize:13, color:'#f85149', fontFamily:'Orbitron, monospace' }}>
                {tail}
              </div>
            ))}
          </div>
        </Card>
      )}

    </div>
  )
}