import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchMetrics, fetchGraph } from '../api/client'
import type { Metrics, GraphData } from '../api/client'

function StatCard({ label, value, sub, color }: { label:string; value:string|number; sub:string; color:string }) {
  return (
    <div className="glass" style={{ padding:'24px 28px' }}>
      <div className="label-caps" style={{ marginBottom:10 }}>{label}</div>
      <div className="stat-number" style={{ color }}>{value}</div>
      <div style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--on-surface-muted)', marginTop:6 }}>{sub}</div>
    </div>
  )
}

export default function SystemTelemetry() {
  const [metrics, setMetrics] = useState<Metrics|null>(null)
  const [graph, setGraph] = useState<GraphData|null>(null)
  const nav = useNavigate()

  useEffect(() => {
    fetchMetrics().then(setMetrics).catch(()=>{})
    fetchGraph().then(setGraph).catch(()=>{})
  }, [])

  const activityData = metrics?.history?.length ? metrics.history : Array.from({length:7}, (_,i) => ({
    queries: 0,
    hits: 0,
  }))

  const topEntities = graph?.nodes.slice().sort((a,b)=>b.importance-a.importance).slice(0,5) ?? []

  return (
    <div className="page-inner fade-in">
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:28 }}>
        <div>
          <h1 style={{ fontFamily:'var(--font-headline)', fontSize:28, fontWeight:700 }}>System Telemetry</h1>
          <p style={{ color:'var(--on-surface-muted)', fontSize:14, marginTop:4 }}>Real-time system diagnostics and metrics.</p>
        </div>
        <button className="btn-primary" onClick={() => nav('/research')}>+ New Research</button>
      </div>

      {/* Stats */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:20, marginBottom:24 }}>
        <StatCard label="Total Entities" value={metrics?.node_count ?? '—'} sub={`+${metrics?.query_count ?? 0} queries run`} color="var(--primary-dim)" />
        <StatCard label="Active Claims" value={metrics?.relationship_count ?? '—'} sub={`${metrics?.claims_accepted ?? 0} accepted`} color="var(--secondary-dim)" />
        <StatCard label="Cache Hit Rate" value={metrics ? `${(metrics.cache_hit_rate*100).toFixed(1)}%` : '—'} sub={`${metrics?.memory_hits ?? 0} hits total`} color="var(--tertiary)" />
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'2fr 1fr', gap:20, marginBottom:24 }}>
        {/* Graph preview */}
        <div className="glass" style={{ padding:24, cursor:'pointer' }} onClick={() => nav('/graph')}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
            <h2 style={{ fontFamily:'var(--font-headline)', fontSize:18, fontWeight:600 }}>Knowledge Graph</h2>
            <span style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--primary)', cursor:'pointer' }}>Open Explorer →</span>
          </div>
          <div style={{ background:'rgba(0,0,0,0.3)', borderRadius:12, padding:20, minHeight:220, display:'flex', flexWrap:'wrap', gap:12, alignContent:'flex-start' }}>
            {(graph?.nodes.slice(0,12) ?? []).map(n => {
              const comm = graph?.communities.find(c => c.id === n.community)
              return (
                <div key={n.id} style={{
                  background:`${comm?.color ?? '#6366f1'}22`,
                  border:`1px solid ${comm?.color ?? '#6366f1'}55`,
                  borderRadius:8, padding:'6px 12px',
                  fontFamily:'var(--font-body)', fontSize:13,
                  color:'var(--on-surface)'
                }}>{n.name}</div>
              )
            })}
          </div>
          <div style={{ marginTop:12, display:'flex', gap:12 }}>
            {graph?.communities.map(c => (
              <div key={c.id} style={{ display:'flex', alignItems:'center', gap:6 }}>
                <div style={{ width:8, height:8, borderRadius:'50%', background:c.color }} />
                <span style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--on-surface-muted)' }}>{c.name ?? `C${c.id}`} ({c.size})</span>
              </div>
            ))}
          </div>
        </div>

        {/* Activity */}
        <div className="glass" style={{ padding:24 }}>
          <h2 style={{ fontFamily:'var(--font-headline)', fontSize:18, fontWeight:600, marginBottom:16 }}>Quick Stats</h2>
          {[
            { label:'Communities', value:metrics?.community_count ?? '—', color:'var(--primary-dim)' },
            { label:'Hub Nodes', value:metrics?.hub_node_count ?? '—', color:'var(--secondary-dim)' },
            { label:'Contradictions', value:metrics?.contradiction_count ?? '—', color:'var(--error)' },
            { label:'Stale Claims', value:metrics?.stale_claims ?? '—', color:'var(--tertiary)' },
            { label:'Avg Latency', value:metrics ? `${metrics.average_latency_ms.toFixed(0)}ms` : '—', color:'var(--on-surface)' },
          ].map(s => (
            <div key={s.label} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'10px 0', borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
              <span style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--on-surface-muted)' }}>{s.label}</span>
              <span style={{ fontFamily:'var(--font-headline)', fontWeight:700, fontSize:18, color:s.color }}>{s.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top entities */}
      <div className="glass" style={{ padding:24 }}>
        <h2 style={{ fontFamily:'var(--font-headline)', fontSize:18, fontWeight:600, marginBottom:20 }}>Top Entities by Importance</h2>
        <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
          {topEntities.map(e => {
            const comm = graph?.communities.find(c => c.id === e.community)
            return (
              <div key={e.id}>
                <div style={{ display:'flex', justifyContent:'space-between', marginBottom:5 }}>
                  <span style={{ fontFamily:'var(--font-body)', fontWeight:600, fontSize:14 }}>{e.name}</span>
                  <span style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--on-surface-muted)' }}>{(e.importance*10).toFixed(1)}</span>
                </div>
                <div style={{ height:4, background:'rgba(255,255,255,0.06)', borderRadius:2, overflow:'hidden' }}>
                  <div style={{ height:'100%', width:`${e.importance*100}%`, background: comm?.color ?? 'var(--secondary)', borderRadius:2, transition:'width 0.8s ease' }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
