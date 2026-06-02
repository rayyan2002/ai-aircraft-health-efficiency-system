import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPakFleet } from '../api'

const AIRLINE_SHORT = {
  'PIA':        'PIA',
  'AirBlue':    'AirBlue',
  'AirSial':    'AirSial',
  'FlyJinnah':  'FlyJinnah',
  'Fly Jinnah': 'FlyJinnah',
  'Pakistan International Airlines': 'PIA',
}

const AIRLINE_COLOR = {
  'PIA':        '#388bfd',
  'Pakistan International Airlines': '#388bfd',
  'AirBlue':    '#3fb950',
  'AirSial':    '#d29922',
  'FlyJinnah':  '#f85149',
  'Fly Jinnah': '#f85149',
}

const FILTER_OPTIONS = ['All', 'PIA', 'AirBlue', 'AirSial', 'FlyJinnah']

export default function FleetOverview() {
  const navigate  = useNavigate()
  const [fleet,   setFleet]   = useState([])
  const [loading, setLoading] = useState(true)
  const [filter,  setFilter]  = useState('All')
  const [sort,    setSort]    = useState('health')

  useEffect(() => {
    getPakFleet()
      .then(r => setFleet(r.data.fleet || []))
      .catch(console.error)
      .finally(() => setLoading(false))
    const iv = setInterval(() => {
      getPakFleet().then(r => setFleet(r.data.fleet || []))
    }, 30000)
    return () => clearInterval(iv)
  }, [])

  const airlines = ['All', ...Object.keys(AIRLINE_SHORT)]
  const filtered = fleet
    .filter(p => {
      if (filter === 'All') return true
      const short = AIRLINE_SHORT[p.airline] || p.airline
      return short === filter || p.airline === filter
    })
    .sort((a, b) => {
      if (sort === 'health')  return (a.health_score||50) - (b.health_score||50)
      if (sort === 'airline') return (a.airline||'').localeCompare(b.airline||'')
      return (a.tail_number||'').localeCompare(b.tail_number||'')
    })

  const healthCol = (s) => s >= 70 ? '#3fb950' : s >= 40 ? '#d29922' : '#f85149'
  const healthBg  = (s) => s >= 70 ? 'rgba(63,185,80,0.08)' : s >= 40 ? 'rgba(210,153,34,0.08)' : 'rgba(248,81,73,0.08)'

  const stats = {
    total:    fleet.length,
    healthy:  fleet.filter(p => (p.health_score||50) >= 70).length,
    moderate: fleet.filter(p => { const h=p.health_score||50; return h>=40&&h<70 }).length,
    critical: fleet.filter(p => (p.health_score||50) < 40).length,
    airborne: fleet.filter(p => p.status === 'airborne').length,
  }

  if (loading) return <div style={{ padding:'32px 40px', color:'#7d8590', fontSize:13 }}>Loading fleet...</div>

  return (
    <div style={{ padding:'32px 40px', maxWidth:1400, margin:'0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom:24 }}>
        <div style={{ fontSize:10, color:'#484f58', letterSpacing:3, textTransform:'uppercase', marginBottom:4 }}>Pakistan Commercial Aviation</div>
        <div style={{ fontFamily:'Orbitron, monospace', fontSize:24, fontWeight:900, color:'#e6edf3' }}>Fleet Overview</div>
        <div style={{ fontSize:13, color:'#7d8590', marginTop:4 }}>All {fleet.length} verified active aircraft</div>
      </div>

      {/* Stats strip */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)', gap:12, marginBottom:24 }}>
        {[
          { label:'Total Fleet',   value:stats.total,    color:'#388bfd' },
          { label:'Airborne',      value:stats.airborne, color:'#3fb950' },
          { label:'Healthy',       value:stats.healthy,  color:'#3fb950' },
          { label:'Moderate Risk', value:stats.moderate, color:'#d29922' },
          { label:'Critical',      value:stats.critical, color:'#f85149' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            background:'#0d1117', border:'1px solid #21262d',
            borderRadius:8, padding:'14px 16px',
          }}>
            <div style={{ fontSize:9, color:'#7d8590', letterSpacing:1.5, textTransform:'uppercase' }}>{label}</div>
            <div style={{ fontFamily:'Orbitron, monospace', fontSize:28, fontWeight:700, color, marginTop:4 }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:20, flexWrap:'wrap' }}>
        <div style={{ display:'flex', gap:8 }}>
          {FILTER_OPTIONS.map(a => (
            <button key={a} onClick={() => setFilter(a)}
              style={{
                padding:'6px 14px', borderRadius:20, fontSize:11, cursor:'pointer',
                border: filter===a ? '1px solid #388bfd' : '1px solid #21262d',
                background: filter===a ? 'rgba(56,139,253,0.15)' : 'transparent',
                color: filter===a ? '#388bfd' : '#7d8590',
              }}>
              {a}
            </button>
          ))}
        </div>
        <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontSize:11, color:'#7d8590' }}>Sort by</span>
          <select value={sort} onChange={e=>setSort(e.target.value)}
            style={{
              background:'#0d1117', border:'1px solid #21262d', color:'#e6edf3',
              padding:'4px 10px', borderRadius:6, fontSize:11, cursor:'pointer'
            }}>
            <option value="health">Health (worst first)</option>
            <option value="airline">Airline</option>
            <option value="tail">Tail Number</option>
          </select>
        </div>
      </div>

      {/* Aircraft grid */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(220px, 1fr))', gap:12 }}>
        {filtered.map(plane => {
          const health  = plane.health_score || 50
          const hCol    = healthCol(health)
          const hBg     = healthBg(health)
          const isAir   = plane.status === 'airborne'
          const aColor  = AIRLINE_COLOR[plane.airline] || '#388bfd'

          return (
            <div key={plane.tail_number}
              onClick={() => navigate(`/pakistan?tail=${plane.tail_number}`)}
              style={{
                background: hBg, border: `1px solid ${hCol}33`,
                borderRadius:10, padding:'16px', cursor:'pointer',
                transition:'all 0.15s', position:'relative', overflow:'hidden'
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor=hCol; e.currentTarget.style.transform='translateY(-2px)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor=`${hCol}33`; e.currentTarget.style.transform='translateY(0)' }}
            >
              {/* Airline color bar */}
              <div style={{ position:'absolute', top:0, left:0, right:0, height:2, background:aColor }} />

              {/* Header row */}
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:10 }}>
                <div>
                  <div style={{ fontFamily:'Orbitron, monospace', fontSize:13, fontWeight:700, color:'#e6edf3' }}>
                    {plane.tail_number}
                  </div>
                  <div style={{ fontSize:10, color:'#7d8590', marginTop:2 }}>
                    {plane.aircraft_type?.split('-')[0] || '—'}
                  </div>
                </div>
                <div style={{
                  fontSize:9, padding:'3px 8px', borderRadius:20,
                  background: isAir ? 'rgba(63,185,80,0.15)' : 'rgba(125,133,144,0.15)',
                  color: isAir ? '#3fb950' : '#7d8590',
                  border: `1px solid ${isAir ? '#3fb950' : '#7d8590'}44`,
                }}>
                  {isAir ? '● AIRBORNE' : '○ GROUND'}
                </div>
              </div>

              {/* Health score */}
              <div style={{ display:'flex', alignItems:'baseline', gap:6, marginBottom:8 }}>
                <div style={{ fontFamily:'Orbitron, monospace', fontSize:32, fontWeight:700, color:hCol }}>
                  {Math.round(health)}
                </div>
                <div style={{ fontSize:11, color:'#7d8590' }}>/ 100</div>
              </div>

              {/* Health bar */}
              <div style={{ height:3, background:'#21262d', borderRadius:2, marginBottom:10 }}>
                <div style={{ height:'100%', width:`${health}%`, background:hCol, borderRadius:2 }} />
              </div>

              {/* Callsign + airline */}
              <div style={{ display:'flex', justifyContent:'space-between', fontSize:10, color:'#484f58' }}>
                <span>{plane.callsign && plane.callsign !== 'Grounded' ? plane.callsign : '—'}</span>
                <span style={{ color:aColor }}>{AIRLINE_SHORT[plane.airline] || plane.airline}</span>
              </div>
            </div>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <div style={{ textAlign:'center', padding:'60px 0', color:'#484f58', fontSize:13 }}>
          No aircraft found for this filter.
        </div>
      )}
    </div>
  )
}