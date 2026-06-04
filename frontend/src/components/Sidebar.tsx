import { NavLink, useLocation } from 'react-router-dom'

const links = [
  { id: 'evolution', label: 'Knowledge Evolution', icon: '📈', path: '/' },
  { id: 'memory', label: 'Memory Explorer', icon: '🧠', path: '/memory' },
  { id: 'research', label: 'Research', icon: '🔍', path: '/research' },
  { id: 'graph', label: 'Knowledge Graph', icon: '🕸️', path: '/graph' },
  { id: 'reports', label: 'Reports', icon: '📋', path: '/reports' },
  { id: 'telemetry', label: 'System Telemetry', icon: '📡', path: '/telemetry' },
]

export default function Sidebar() {
  return (
    <nav style={{
      width: 228, minWidth: 228, background: 'var(--bg-surface-low)',
      borderRight: '1px solid rgba(255,255,255,0.07)',
      display: 'flex', flexDirection: 'column', padding: '24px 0', height: '100vh',
      position: 'sticky', top: 0
    }}>
      {/* Logo */}
      <div style={{ padding: '0 20px 28px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
        <NavLink to="/" style={{ textDecoration: 'none' }}>
          <div style={{ display:'flex', alignItems:'center', gap:10 }}>
            <div style={{
              width:36, height:36, borderRadius:'50%',
              background:'rgba(99,102,241,0.2)', border:'1px solid rgba(99,102,241,0.4)',
              display:'flex', alignItems:'center', justifyContent:'center', fontSize:18
            }}>🧠</div>
            <div>
              <div style={{ fontFamily:'var(--font-headline)', fontWeight:700, fontSize:15, color:'var(--primary-dim)' }}>MemoriaAI</div>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--on-surface-muted)', letterSpacing:'0.08em' }}>RESEARCH HUB</div>
            </div>
          </div>
        </NavLink>
      </div>

      {/* Nav links */}
      <div style={{ flex:1, padding:'16px 12px', display:'flex', flexDirection:'column', gap:4 }}>
        {links.map(l => (
          <NavLink key={l.id} to={l.path} style={({ isActive }) => ({
            display:'flex', alignItems:'center', gap:10,
            padding:'10px 12px', borderRadius:8, textDecoration:'none',
            fontFamily:'var(--font-body)', fontSize:14, fontWeight: isActive ? 600 : 400,
            color: isActive ? 'var(--primary-dim)' : 'var(--on-surface-var)',
            background: isActive ? 'rgba(99,102,241,0.12)' : 'transparent',
            boxShadow: isActive ? '0 0 0 1px rgba(99,102,241,0.2) inset' : 'none',
            transition: 'all 0.15s'
          })}>
            <span style={{ fontSize:16 }}>{l.icon}</span>
            {l.label}
          </NavLink>
        ))}
      </div>

      {/* Footer */}
      <div style={{ padding:'16px 20px', borderTop:'1px solid rgba(255,255,255,0.07)' }}>
        <div style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--on-surface-muted)', lineHeight:1.8 }}>
          <div style={{ color:'var(--secondary-dim)', marginBottom:2 }}>● API: localhost:8000</div>
          MemoriaAI v1.0.0
        </div>
      </div>
    </nav>
  )
}
