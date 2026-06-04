import { useEffect, useState } from 'react'
import { fetchEntities, fetchClaims, fetchContradictions } from '../api/client'

type Tab = 'entities'|'claims'|'contradictions'

export default function MemoryExplorer() {
  const [tab, setTab] = useState<Tab>('entities')
  const [entities, setEntities] = useState<any[]>([])
  const [claims, setClaims] = useState<any[]>([])
  const [contradictions, setContradictions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchEntities(), fetchClaims(), fetchContradictions()])
      .then(([e, c, ct]) => {
        setEntities(e.entities ?? [])
        setClaims(c.claims ?? [])
        setContradictions(ct.contradictions ?? [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const filteredEntities = entities.filter(e => !search || e.name?.toLowerCase().includes(search.toLowerCase()))
  const filteredClaims = claims.filter(c => !search || c.source?.toLowerCase().includes(search.toLowerCase()) || c.target?.toLowerCase().includes(search.toLowerCase()))

  const tabs: { key:Tab; label:string; count:number }[] = [
    { key:'entities', label:'Entities', count:entities.length },
    { key:'claims', label:'Claims', count:claims.length },
    { key:'contradictions', label:'Contradictions', count:contradictions.length },
  ]

  return (
    <div className="page-inner fade-in">
      <h1 style={{ fontFamily:'var(--font-headline)', fontSize:28, fontWeight:700, marginBottom:6 }}>Memory Explorer</h1>
      <p style={{ color:'var(--on-surface-muted)', fontSize:14, marginBottom:28 }}>Browse entities, claims, and contradictions stored in the knowledge graph.</p>

      {/* Tabs + search */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <div style={{ display:'flex', gap:4, borderBottom:'1px solid rgba(255,255,255,0.06)', paddingBottom:0 }}>
          {tabs.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              style={{
                background:'none', border:'none', cursor:'pointer', padding:'10px 18px',
                fontFamily:'var(--font-mono)', fontSize:12,
                color: tab===t.key ? 'var(--primary-dim)' : 'var(--on-surface-muted)',
                borderBottom: tab===t.key ? '2px solid var(--primary)' : '2px solid transparent',
              }}>
              {t.label} <span style={{ marginLeft:6, fontFamily:'var(--font-mono)', fontSize:10, opacity:0.6 }}>({t.count})</span>
            </button>
          ))}
        </div>
        <input className="input-dark" placeholder="Search..." value={search} onChange={e=>setSearch(e.target.value)} style={{ width:220 }} />
      </div>

      {loading && <div style={{ padding:40, textAlign:'center', color:'var(--on-surface-muted)' }}>Loading memory...</div>}

      {/* Entities */}
      {!loading && tab === 'entities' && (
        <div className="glass" style={{ padding:8 }}>
          <table className="data-table">
            <thead><tr><th>Name</th><th>Type</th><th>Importance</th><th>Community</th><th>Claims</th><th>Authority</th></tr></thead>
            <tbody>
              {filteredEntities.map((e,i) => (
                <tr key={i}>
                  <td style={{ color:'var(--on-surface)', fontWeight:600 }}>{e.name}</td>
                  <td><span className="chip chip-indigo" style={{ fontSize:10 }}>{e.type}</span></td>
                  <td>
                    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                      <div style={{ flex:1, height:4, background:'rgba(255,255,255,0.06)', borderRadius:2 }}>
                        <div style={{ height:'100%', width:`${(e.importance??0)*100}%`, background:'var(--secondary)', borderRadius:2 }} />
                      </div>
                      <span style={{ fontFamily:'var(--font-mono)', fontSize:11, minWidth:30 }}>{((e.importance??0)*10).toFixed(1)}</span>
                    </div>
                  </td>
                  <td><span className="chip chip-purple" style={{ fontSize:10 }}>C{e.community ?? 0}</span></td>
                  <td style={{ fontFamily:'var(--font-mono)', fontSize:12 }}>{e.claim_count ?? e.degree ?? '—'}</td>
                  <td style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--secondary-dim)' }}>{e.source_authority ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Claims */}
      {!loading && tab === 'claims' && (
        <div className="glass" style={{ padding:8 }}>
          <table className="data-table">
            <thead><tr><th>Source</th><th>Predicate</th><th>Target</th><th>Confidence</th><th>Status</th><th>Version</th></tr></thead>
            <tbody>
              {filteredClaims.map((c,i) => (
                <tr key={i}>
                  <td style={{ color:'var(--primary-dim)', fontWeight:600 }}>{c.source}</td>
                  <td><span className="chip chip-indigo" style={{ fontSize:10 }}>{c.predicate}</span></td>
                  <td style={{ color:'var(--secondary-dim)' }}>{c.target}</td>
                  <td>
                    <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                      <div style={{ width:40, height:4, background:'rgba(255,255,255,0.06)', borderRadius:2 }}>
                        <div style={{ height:'100%', width:`${(c.confidence??0)*100}%`, background: (c.confidence??0) > 0.85 ? 'var(--secondary)' : 'var(--tertiary)', borderRadius:2 }} />
                      </div>
                      <span style={{ fontFamily:'var(--font-mono)', fontSize:11 }}>{((c.confidence??0)*100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td><span className={`chip ${c.status==='verified'?'chip-green':c.status==='pending'?'chip-amber':'chip-red'}`} style={{ fontSize:10 }}>{c.status ?? 'pending'}</span></td>
                  <td style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--on-surface-muted)' }}>v{c.version ?? 1}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Contradictions */}
      {!loading && tab === 'contradictions' && (
        <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
          {contradictions.length === 0 && (
            <div style={{ padding:40, textAlign:'center', color:'var(--on-surface-muted)' }}>✅ No contradictions detected.</div>
          )}
          {contradictions.map((c,i) => (
            <div key={i} className="glass" style={{ padding:20, borderLeft:`3px solid ${c.resolution==='UNRESOLVED'?'var(--error)':'var(--tertiary)'}` }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:10 }}>
                <div style={{ fontFamily:'var(--font-headline)', fontWeight:700, fontSize:16 }}>{c.entity}</div>
                <div style={{ display:'flex', gap:8 }}>
                  <span className={`chip ${c.priority==='HIGH'?'chip-red':'chip-amber'}`} style={{ fontSize:10 }}>{c.priority}</span>
                  <span className={`chip ${c.resolution==='UNRESOLVED'?'chip-red':'chip-purple'}`} style={{ fontSize:10 }}>{c.resolution}</span>
                </div>
              </div>
              <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
                {c.conflicting_claims?.map((claim:string, j:number) => (
                  <div key={j} style={{ padding:'8px 12px', background:'rgba(255,255,255,0.03)', borderRadius:6, fontSize:13, color:'var(--on-surface-var)', fontFamily:'var(--font-mono)' }}>
                    {claim}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
