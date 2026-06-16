// Shared industry-grade UI primitives for AeroTwin
// Dark command-center aesthetic. Import these across pages for consistency.

export const C = {
  bg:     '#060810',
  card:   '#0d1117',
  hover:  '#161b22',
  border: '#21262d',
  accent: '#388bfd',
  green:  '#3fb950',
  yellow: '#d29922',
  red:    '#f85149',
  text:   '#e6edf3',
  muted:  '#7d8590',
  dim:    '#484f58',
}

export function Page({ title, subtitle, eyebrow, right, children }) {
  return (
    <div style={{ padding: '28px 36px', maxWidth: 1500, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          {eyebrow && <div style={{ fontSize: 10, color: C.dim, letterSpacing: 3, textTransform: 'uppercase', marginBottom: 4 }}>{eyebrow}</div>}
          <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 24, fontWeight: 900, color: C.text }}>{title}</div>
          {subtitle && <div style={{ fontSize: 13, color: C.muted, marginTop: 4 }}>{subtitle}</div>}
        </div>
        {right}
      </div>
      <div style={{ height: 1, background: 'linear-gradient(90deg, #21262d, transparent)', marginBottom: 24 }} />
      {children}
    </div>
  )
}

export function Card({ children, style = {}, hover = false, onClick }) {
  const base = {
    background: C.card, border: `1px solid ${C.border}`,
    borderRadius: 12, padding: '18px 20px', ...style,
  }
  const handlers = hover ? {
    onMouseEnter: e => (e.currentTarget.style.borderColor = C.accent),
    onMouseLeave: e => (e.currentTarget.style.borderColor = C.border),
  } : {}
  return <div onClick={onClick} style={base} {...handlers}>{children}</div>
}

export function Label({ children }) {
  return <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: 2, textTransform: 'uppercase', color: C.muted, marginBottom: 8 }}>{children}</div>
}

export function Kpi({ label, value, unit, color }) {
  return (
    <Card style={{ position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: color || C.accent }} />
      <Label>{label}</Label>
      <div style={{ fontFamily: 'Orbitron, monospace', fontSize: 26, fontWeight: 700, color: color || C.text, lineHeight: 1 }}>{value}</div>
      {unit && <div style={{ fontSize: 11, color: C.dim, marginTop: 4 }}>{unit}</div>}
    </Card>
  )
}

export function Pill({ active, onClick, children, color = C.accent }) {
  return (
    <button onClick={onClick} style={{
      padding: '6px 16px', borderRadius: 20, fontSize: 12, cursor: 'pointer',
      border: active ? `1px solid ${color}` : `1px solid ${C.border}`,
      background: active ? `${color}22` : 'transparent',
      color: active ? color : C.muted, transition: 'all 0.15s',
    }}>{children}</button>
  )
}

export function Badge({ children, color = C.muted, fill }) {
  return (
    <span style={{
      fontSize: 10, padding: '3px 9px', borderRadius: 20, fontWeight: 500,
      background: fill || `${color}22`, color, border: `1px solid ${color}44`,
      whiteSpace: 'nowrap',
    }}>{children}</span>
  )
}

export function Bar({ value, max = 100, color = C.accent, height = 6 }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div style={{ height, background: C.border, borderRadius: height / 2, overflow: 'hidden' }}>
      <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: height / 2, transition: 'width 0.6s ease' }} />
    </div>
  )
}

export function Empty({ children }) {
  return <div style={{ textAlign: 'center', padding: '60px 0', color: C.dim, fontSize: 13 }}>{children}</div>
}

export function Spinner({ text = 'Loading...' }) {
  return <div style={{ padding: '40px 0', textAlign: 'center', color: C.muted, fontSize: 13 }}>{text}</div>
}
