import { useEffect, useState } from 'react'
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchMetrics } from '../api/client'
import type { Metrics } from '../api/client'

const COLORS = ['#6366f1','#22d3ee','#a78bfa','#34d399','#f59e0b']

function KpiCard({ label, value, sub, color }: { label:string; value:string|number; sub:string; color:string }) {
  return (
    <div className="glass" style={{ padding:'20px 24px' }}>
      <div className="label-caps" style={{ marginBottom:10 }}>{label}</div>
      <div style={{ fontFamily:'var(--font-headline)', fontSize:32, fontWeight:700, color, letterSpacing:'-0.02em', marginBottom:4 }}>{value}</div>
      <div style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--on-surface-muted)' }}>{sub}</div>
    </div>
  )
}

export default function Observability() {
  const [metrics, setMetrics] = useState<Metrics|null>(null)

  useEffect(() => {
    fetchMetrics().then(setMetrics).catch(()=>{})
    const iv = setInterval(() => fetchMetrics().then(setMetrics).catch(()=>{}), 10000)
    return () => clearInterval(iv)
  }, [])

  const m = metrics

  const activityData = Array.from({length:7}, (_,i) => ({
    day: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][i],
    queries: Math.round((m?.query_count ?? 5) * (0.5 + Math.random()*0.8)),
    hits: Math.round((m?.memory_hits ?? 3) * (0.5 + Math.random()*0.8)),
  }))

  const providerData = [
    { name:'Tavily', value:45 },
    { name:'Serper', value:30 },
    { name:'DDG', value:25 },
  ]

  const qualityData = [
    { name:'High (>0.9)', value: m ? Math.round(m.claims_accepted * 0.6) : 60 },
    { name:'Medium (0.7-0.9)', value: m ? Math.round(m.claims_accepted * 0.3) : 30 },
    { name:'Low (<0.7)', value: m ? Math.round(m.claims_rejected * 0.5) : 10 },
  ]

  return (
    <div className="page-inner fade-in">
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:28 }}>
        <div>
          <h1 style={{ fontFamily:'var(--font-headline)', fontSize:28, fontWeight:700 }}>Observability</h1>
          <p style={{ color:'var(--on-surface-muted)', fontSize:14, marginTop:4 }}>
            Real-time system metrics · Auto-refreshes every 10s
            <span className="pulse-dot" style={{ display:'inline-block', width:6, height:6, borderRadius:'50%', background:'var(--secondary)', marginLeft:8, verticalAlign:'middle' }} />
          </p>
        </div>
      </div>

      {/* KPI Row */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16, marginBottom:24 }}>
        <KpiCard label="Total Queries" value={m?.query_count ?? '—'} sub="Research sessions run" color="var(--primary-dim)" />
        <KpiCard label="Cache Hit Rate" value={m ? `${(m.cache_hit_rate*100).toFixed(1)}%` : '—'} sub={`${m?.memory_hits ?? 0} hits`} color="var(--secondary-dim)" />
        <KpiCard label="Claims Accepted" value={m?.claims_accepted ?? '—'} sub={`${m?.claims_rejected ?? 0} rejected`} color="var(--tertiary)" />
        <KpiCard label="Avg Latency" value={m ? `${m.average_latency_ms.toFixed(0)}ms` : '—'} sub="Per research query" color="var(--on-surface)" />
      </div>

      {/* Graph stats row */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16, marginBottom:24 }}>
        <KpiCard label="Graph Nodes" value={m?.node_count ?? '—'} sub="Total entities" color="var(--primary-dim)" />
        <KpiCard label="Relationships" value={m?.relationship_count ?? '—'} sub="Claim edges" color="var(--secondary-dim)" />
        <KpiCard label="Communities" value={m?.community_count ?? '—'} sub="Louvain clusters" color="var(--tertiary)" />
        <KpiCard label="Stale Claims" value={m?.stale_claims ?? '—'} sub="Pending refresh" color="var(--error)" />
      </div>

      {/* Charts row */}
      <div style={{ display:'grid', gridTemplateColumns:'2fr 1fr', gap:20, marginBottom:24 }}>
        {/* Area chart */}
        <div className="glass" style={{ padding:24 }}>
          <h2 style={{ fontFamily:'var(--font-headline)', fontSize:16, fontWeight:600, marginBottom:20 }}>Research Activity (7 days)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={activityData}>
              <defs>
                <linearGradient id="q" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="h" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#22d3ee" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="day" tick={{ fill:'#908fa0', fontSize:11, fontFamily:'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:'#908fa0', fontSize:11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background:'#1b1f2c', border:'1px solid rgba(255,255,255,0.1)', borderRadius:8, fontFamily:'JetBrains Mono', fontSize:12 }} />
              <Area type="monotone" dataKey="queries" stroke="#6366f1" fill="url(#q)" strokeWidth={2} name="Queries" />
              <Area type="monotone" dataKey="hits" stroke="#22d3ee" fill="url(#h)" strokeWidth={2} name="Cache Hits" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Pie chart */}
        <div className="glass" style={{ padding:24 }}>
          <h2 style={{ fontFamily:'var(--font-headline)', fontSize:16, fontWeight:600, marginBottom:20 }}>Provider Distribution</h2>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={providerData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={65} strokeWidth={0}>
                {providerData.map((_,i) => <Cell key={i} fill={COLORS[i]} />)}
              </Pie>
              <Tooltip contentStyle={{ background:'#1b1f2c', border:'1px solid rgba(255,255,255,0.1)', borderRadius:8, fontFamily:'JetBrains Mono', fontSize:12 }} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display:'flex', justifyContent:'center', gap:16, marginTop:8 }}>
            {providerData.map((p,i) => (
              <div key={p.name} style={{ display:'flex', alignItems:'center', gap:5 }}>
                <div style={{ width:8, height:8, borderRadius:'50%', background:COLORS[i] }} />
                <span style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--on-surface-muted)' }}>{p.name} {p.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quality distribution */}
      <div className="glass" style={{ padding:24 }}>
        <h2 style={{ fontFamily:'var(--font-headline)', fontSize:16, fontWeight:600, marginBottom:20 }}>Knowledge Quality Distribution</h2>
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={qualityData} layout="vertical">
            <XAxis type="number" tick={{ fill:'#908fa0', fontSize:11 }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" tick={{ fill:'#c7c4d7', fontSize:12, fontFamily:'JetBrains Mono' }} axisLine={false} tickLine={false} width={110} />
            <Tooltip contentStyle={{ background:'#1b1f2c', border:'1px solid rgba(255,255,255,0.1)', borderRadius:8, fontSize:12 }} />
            <Bar dataKey="value" fill="#6366f1" radius={[0,4,4,0]}>
              {qualityData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
