import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 20000 })

// ── Live Dashboard ──
export const getLiveFleet    = ()      => api.get('/live_fleet')
export const analyzeLive     = (tail)  => api.get(`/analyze/${tail}`)
export const getLiveRoute    = (tail)  => api.get(`/route/${tail}`)
export const getLiveMap      = ()      => api.get('/live_map')
export const getLiveTrack    = (cs)    => api.get(`/live_track/${cs}`)
export const getHistory      = (tail)  => api.get(`/history/${tail}`)

// ── Pakistan Fleet ──
export const getPakFleet     = ()      => api.get('/pak_fleet')
export const analyzePak      = (tail)  => api.get(`/pak_analyze/${tail}`)
export const getPakRoute     = (tail)  => api.get(`/pak_route/${tail}`)
export const getPakHistory   = (tail)  => api.get(`/pak_history/${tail}`)

// ── Maintenance ──
export const getMaintHistory = (tail)  => api.get(`/maintenance_history/${tail}`)
export const logMaintenance  = (data)  => api.post('/log_maintenance', data)

// ── Fleet status / pipeline ──
export const getFleetStatus  = ()      => api.get('/fleet_status')
export const getPipelineLogs = ()      => api.get('/pipeline_logs')

// ── Weather ──
export const getWeather      = ()      => api.get('/weather')

// ── Simulator ──
export const simulate        = (data)  => api.post('/simulate', data)

// ── Helpers ──────────────────────────────────────────────
export const AIRLINE_ALIAS = {
  'PIA': 'PIA',
  'Pakistan International Airlines': 'PIA',
  'AirBlue': 'AirBlue',
  'AirSial': 'AirSial',
  'FlyJinnah': 'FlyJinnah',
  'Fly Jinnah': 'FlyJinnah',
}

export const AIRLINE_COLOR = {
  'PIA': '#388bfd',
  'Pakistan International Airlines': '#388bfd',
  'AirBlue': '#3fb950',
  'AirSial': '#d29922',
  'FlyJinnah': '#f85149',
  'Fly Jinnah': '#f85149',
}

export const shortAirline = (a) => AIRLINE_ALIAS[a] || a || '—'

export const healthColor = (s) => (s >= 70 ? '#3fb950' : s >= 40 ? '#d29922' : '#f85149')
export const riskColor   = (r) => (r === 'Low' ? '#3fb950' : r === 'Moderate' ? '#d29922' : '#f85149')

export const toIATA = (cs = '') => {
  if (!cs || cs === 'Grounded') return '—'
  const map = { PIA: 'PK', ABQ: 'PA', FJL: '9P', SIF: 'PF' }
  for (const [icao, iata] of Object.entries(map)) {
    if (cs.startsWith(icao)) return iata + cs.slice(icao.length)
  }
  return cs
}

export const CO2_PER_FUEL = 2.53