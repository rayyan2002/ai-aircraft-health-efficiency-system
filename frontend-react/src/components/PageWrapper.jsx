export default function PageWrapper({ children, title, subtitle }) {
  return (
    <div style={{ padding: '32px 40px', maxWidth: 1400, margin: '0 auto' }}>
      {(title || subtitle) && (
        <div style={{ marginBottom: 32 }}>
          {title && (
            <div style={{
              fontFamily: 'Orbitron, monospace', fontSize: 24,
              fontWeight: 900, color: '#e6edf3', letterSpacing: 2,
            }}>
              {title}
            </div>
          )}
          {subtitle && (
            <div style={{ fontSize: 13, color: '#7d8590', marginTop: 4 }}>
              {subtitle}
            </div>
          )}
          <div style={{
            marginTop: 16, height: 1,
            background: 'linear-gradient(90deg, #21262d, transparent)',
          }} />
        </div>
      )}
      {children}
    </div>
  )
}
