export default function KpiCard({ label, value, unit, color }) {
  return (
    <div style={{
      background: '#0d1117', border: '1px solid #21262d',
      borderRadius: 8, padding: '16px 20px', position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0,
        height: 2, background: color || '#388bfd',
      }} />
      <div style={{
        fontSize: 10, fontWeight: 600, letterSpacing: 2,
        textTransform: 'uppercase', color: '#7d8590', marginBottom: 8,
      }}>{label}</div>
      <div style={{
        fontFamily: 'Orbitron, monospace', fontSize: 28,
        fontWeight: 700, color: color || '#e6edf3', lineHeight: 1,
      }}>{value}</div>
      {unit && <div style={{ fontSize: 11, color: '#7d8590', marginTop: 4 }}>{unit}</div>}
    </div>
  )
}
