import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 15000 })

// ── Live Dashboard ──
export const getLiveFleet   = ()     => api.get('/live_fleet')
export const analyzeAircraft = (tail) => api.get(`/analyze/${tail}`)
export const getRoute        = (tail) => api.get(`/route/${tail}`)

// ── Pakistan Fleet ──
export const getPakFleet    = ()     => api.get('/pak_fleet')
export const analyzePak     = (tail) => api.get(`/pak_analyze/${tail}`)
export const getPakRoute    = (tail) => api.get(`/pak_route/${tail}`)
export const getPakHistory  = (tail) => api.get(`/pak_history/${tail}`)

// ── Maintenance ──
export const getMaintHistory = (tail) => api.get(`/maintenance_history/${tail}`)
export const logMaintenance  = (data) => api.post('/log_maintenance', data)

// ── Fleet ──
export const getFleetStatus  = ()     => api.get('/fleet_status')
export const getPipelineLogs = ()     => api.get('/pipeline_logs')

// ── Weather ──
export const getWeather      = ()     => api.get('/weather')

// ── Simulator ──
export const simulate        = (data) => api.post('/simulate', data)

// ── Anomaly feed ──
export const getAnomalies    = ()     => api.get('/anomaly_feed')

// ── IATA flight number converter ──
export const toIATA = (callsign = '') => {
  const map = { PIA: 'PK', ABQ: 'PA', FJL: '9P', SIF: 'PF', ERD: 'PF' }
  for (const [icao, iata] of Object.entries(map)) {
    if (callsign.startsWith(icao)) return iata + callsign.slice(icao.length)
  }
  return callsign
}

// ── Health colour helper ──
export const healthColor = (score) => {
  if (score >= 70) return '#3fb950'
  if (score >= 40) return '#d29922'
  return '#f85149'
}

export const riskColor = (risk) => {
  if (risk === 'Low')      return '#3fb950'
  if (risk === 'Moderate') return '#d29922'
  return '#f85149'
}
