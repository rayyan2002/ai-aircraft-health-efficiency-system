import { useState } from 'react'
import { recomputeFleetHealth } from '../api'
import { C } from './ui'

/**
 * "Recompute Predictions" — the demo trick.
 *
 * Normal page loads read cached health (instant, professional).
 * This button forces every aircraft back through the LSTM, live, with a
 * visible progress bar and a report of how many models ran and how long it
 * took. Use it when someone asks "is this actually a real model?"
 *
 * The proof is threefold:
 *   1. The progress bar and elapsed time (real inference takes real time)
 *   2. The backend terminal fills with per-aircraft LSTM predictions
 *   3. The numbers come back IDENTICAL — deterministic, not random
 *
 * props:
 *   onDone(fleetArray)  called with fresh results
 */
export default function RecomputeButton({ onDone = () => {} }) {
  const [running, setRunning] = useState(false)
  const [pct, setPct]         = useState(0)
  const [report, setReport]   = useState(null)

  const run = async () => {
    setRunning(true)
    setReport(null)
    setPct(0)

    // Progress is indicative — the server computes as one batch, so we animate
    // toward 90% and snap to 100% when the real response lands. We never claim
    // per-aircraft progress we don't actually have.
    const timer = setInterval(() => {
      setPct(p => (p < 90 ? p + Math.random() * 7 : p))
    }, 260)

    const t0 = performance.now()
    try {
      const r = await recomputeFleetHealth()
      const wall = Math.round(performance.now() - t0)
      clearInterval(timer)
      setPct(100)

      setReport({
        computed:   r.data.computed,
        total:      r.data.total,
        serverMs:   r.data.elapsed_ms,
        wallMs:     wall,
        model:      r.data.model,
        avg:        r.data.summary?.avg_health,
      })
      onDone(r.data.fleet || [])
    } catch (e) {
      clearInterval(timer)
      setPct(0)
      setReport({ error: 'Recompute failed — is the backend running?' })
    } finally {
      setRunning(false)
      setTimeout(() => setPct(0), 1200)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 230 }}>
      <button
        onClick={run}
        disabled={running}
        title="Force every aircraft back through the LSTM model"
        style={{
          padding: '8px 16px', borderRadius: 8, fontSize: 12, fontWeight: 600,
          cursor: running ? 'wait' : 'pointer',
          border: `1px solid ${running ? C.accent : C.border}`,
          background: running ? 'rgba(56,139,253,0.15)' : 'transparent',
          color: running ? C.accent : C.muted,
          display: 'flex', alignItems: 'center', gap: 7, justifyContent: 'center',
          transition: 'all .15s',
        }}
        onMouseEnter={e => { if (!running) e.currentTarget.style.borderColor = C.accent }}
        onMouseLeave={e => { if (!running) e.currentTarget.style.borderColor = C.border }}
      >
        <span style={{
          display: 'inline-block',
          animation: running ? 'spin 1s linear infinite' : 'none',
        }}>⟳</span>
        {running ? 'Running the model…' : 'Recompute predictions'}
      </button>

      {/* progress */}
      {(running || pct > 0) && (
        <div style={{ height: 3, background: C.border, borderRadius: 2, overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${pct}%`, background: C.accent,
            transition: 'width .3s ease',
          }} />
        </div>
      )}

      {/* proof panel */}
      {report && !report.error && (
        <div style={{
          fontSize: 10, color: C.muted, lineHeight: 1.6,
          background: 'rgba(63,185,80,0.06)', border: '1px solid rgba(63,185,80,0.3)',
          borderRadius: 6, padding: '7px 9px',
        }}>
          <div style={{ color: '#3fb950', fontWeight: 600, marginBottom: 2 }}>
            ✓ {report.computed} of {report.total} aircraft re-predicted
          </div>
          <div>Model: <span style={{ color: C.text }}>{report.model}</span></div>
          <div>Inference time: <span style={{ color: C.text }}>{report.serverMs} ms</span> server
            {' · '}{report.wallMs} ms round-trip</div>
          {report.avg != null && (
            <div>Fleet mean health: <span style={{ color: C.text }}>{report.avg}</span></div>
          )}
          <div style={{ color: C.dim, marginTop: 3 }}>
            Values are deterministic — recomputing returns the same result.
          </div>
        </div>
      )}

      {report?.error && (
        <div style={{ fontSize: 10, color: C.red }}>{report.error}</div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0) } to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}