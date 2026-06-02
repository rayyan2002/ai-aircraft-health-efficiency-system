import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import './index.css'

import Home           from './pages/Home'
import Dashboard      from './pages/Dashboard'
import FleetOverview  from './pages/FleetOverview'
import PakistanFleet  from './pages/PakistanFleet'
import MissionLogs    from './pages/MissionLogs'
import Maintenance    from './pages/Maintenance'
import Simulator      from './pages/Simulator'
import MaintenanceCal from './pages/MaintenanceCal'
import CO2Dashboard   from './pages/CO2Dashboard'
import AnomalyFeed    from './pages/AnomalyFeed'
import RouteAnalyzer  from './pages/RouteAnalyzer'
import TwinCompare    from './pages/TwinCompare'

const NAV = [
  { to: '/',            label: 'Home',           icon: '⌂' },
  { to: '/dashboard',   label: 'Live',            icon: '📡' },
  { to: '/fleet',       label: 'Fleet',           icon: '✈' },
  { to: '/pakistan',    label: 'Pakistan',        icon: '🇵🇰' },
  { to: '/logs',        label: 'Logs',            icon: '📋' },
  { to: '/maintenance', label: 'Maintenance',     icon: '🔧' },
  { to: '/simulator',   label: 'Simulator',       icon: '🧮' },
  { to: '/calendar',    label: 'Schedule',        icon: '📅' },
  { to: '/co2',         label: 'CO₂',             icon: '🌿' },
  { to: '/anomalies',   label: 'Anomalies',       icon: '⚠' },
  { to: '/route',       label: 'Route',           icon: '🗺' },
  { to: '/compare',     label: 'Compare',         icon: '⚖' },
]

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', minHeight: '100vh' }}>

        {/* ── Sidebar ── */}
        <aside style={{
          width: 220, flexShrink: 0, background: '#0d1117',
          borderRight: '1px solid #21262d', padding: '24px 0',
          display: 'flex', flexDirection: 'column', position: 'sticky',
          top: 0, height: '100vh', overflowY: 'auto',
        }}>
          {/* Brand */}
          <div style={{ padding: '0 20px 24px' }}>
            <div style={{
              fontFamily: 'Orbitron, monospace', fontSize: 18,
              fontWeight: 900, color: '#388bfd', letterSpacing: 2,
            }}>AEROTWIN</div>
            <div style={{ fontSize: 10, color: '#484f58', marginTop: 4 }}>
              Pakistan Digital Fleet
            </div>
          </div>

          {/* Nav links */}
          <nav style={{ flex: 1 }}>
            {NAV.map(({ to, label, icon }) => (
              <NavLink key={to} to={to} end={to === '/'}
                style={({ isActive }) => ({
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 20px', fontSize: 13, textDecoration: 'none',
                  color: isActive ? '#e6edf3' : '#7d8590',
                  background: isActive ? '#161b22' : 'transparent',
                  borderRight: isActive ? '2px solid #388bfd' : '2px solid transparent',
                  transition: 'all 0.15s',
                })}
              >
                <span style={{ fontSize: 14 }}>{icon}</span>
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Footer */}
          <div style={{ padding: '16px 20px', fontSize: 10, color: '#484f58' }}>
            AeroTwin v3.0 · Sprint 4
          </div>
        </aside>

        {/* ── Main content ── */}
        <main style={{ flex: 1, overflowY: 'auto', minWidth: 0 }}>
          <Routes>
            <Route path="/"            element={<Home />} />
            <Route path="/dashboard"   element={<Dashboard />} />
            <Route path="/fleet"       element={<FleetOverview />} />
            <Route path="/pakistan"    element={<PakistanFleet />} />
            <Route path="/logs"        element={<MissionLogs />} />
            <Route path="/maintenance" element={<Maintenance />} />
            <Route path="/simulator"   element={<Simulator />} />
            <Route path="/calendar"    element={<MaintenanceCal />} />
            <Route path="/co2"         element={<CO2Dashboard />} />
            <Route path="/anomalies"   element={<AnomalyFeed />} />
            <Route path="/route"       element={<RouteAnalyzer />} />
            <Route path="/compare"     element={<TwinCompare />} />
          </Routes>
        </main>

      </div>
    </BrowserRouter>
  )
}
