import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AreaChart, Area, BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchMetrics } from '../api/client'
import type { Metrics } from '../api/client'

function MetricCard({ label, value, sub, highlight }: { label:string; value:string|number; sub:string; highlight?:boolean }) {
  return (
    <div className="glass" style={{ padding:'24px 28px', border: highlight ? '1px solid rgba(99,102,241,0.4)' : undefined, background: highlight ? 'rgba(99,102,241,0.04)' : undefined }}>
      <div className="label-caps" style={{ marginBottom:10, color: highlight ? 'var(--primary-dim)' : 'var(--on-surface-muted)' }}>{label}</div>
      <div style={{ fontFamily:'var(--font-headline)', fontSize:36, fontWeight:700, color: highlight ? 'var(--primary)' : 'var(--on-surface)', letterSpacing:'-0.02em', marginBottom:6 }}>{value}</div>
      <div style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--on-surface-muted)' }}>{sub}</div>
    </div>
  )
}

export default function KnowledgeEvolution() {
  const [metrics, setMetrics] = useState<Metrics|null>(null)
  const nav = useNavigate()

  useEffect(() => {
    fetchMetrics().then(setMetrics).catch(()=>{})
  }, [])

  const m = metrics

  // Real historical data from backend tracking
  const growthData = m?.history || []

  const maturityStage = m?.maturity_stage || 'Calculating...'
  const maturityScore = m?.maturity_score || 0
  
  // Calculate width for the progress bar (max score ~ 1000 for full bar)
  const progressPercent = Math.min(100, Math.max(5, (maturityScore / 1000) * 100))

  const expSearches = m?.expected_searches || 12;
  const actSearches = m?.actual_searches ?? 4;

  return (
    <div className="page-inner fade-in">
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:28 }}>
        <div>
          <h1 style={{ fontFamily:'var(--font-headline)', fontSize:28, fontWeight:700 }}>Knowledge Evolution</h1>
          <p style={{ color:'var(--on-surface-muted)', fontSize:14, marginTop:4 }}>
            System intelligence compounding and research efficiency metrics.
          </p>
        </div>
        <button className="btn-primary" onClick={() => nav('/research')}>+ New Research</button>
      </div>

      {/* Hero Metrics - Proving the value */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:20, marginBottom:24 }}>
        <MetricCard 
          label="Memory Reuse Rate" 
          value={m ? `${(m.memory_reuse_rate * 100).toFixed(1)}%` : '—'} 
          sub="Queries answered from memory" 
          highlight 
        />
        <MetricCard 
          label="Searches Avoided" 
          value={m?.searches_avoided ?? '—'} 
          sub="Redundant queries bypassed" 
        />
        <MetricCard 
          label="Estimated Research Time Saved" 
          value={m ? `${m.time_saved_hours}h` : '—'} 
          sub="Based on 2.15m per search avoided" 
        />
        <MetricCard 
          label="Learning Efficiency" 
          value={m ? `${m.learning_efficiency}/100` : '—'} 
          sub="System utility score" 
        />
      </div>

      {/* Research Savings (Before vs After) */}
      <div className="glass" style={{ padding:28, marginBottom:24, display:'flex', gap:40, alignItems:'center' }}>
        <div style={{ flex:1 }}>
          <h2 style={{ fontFamily:'var(--font-headline)', fontSize:20, fontWeight:700, marginBottom:8 }}>Research Savings</h2>
          <p style={{ color:'var(--on-surface-muted)', fontSize:14, lineHeight:1.6 }}>
            As the system accumulates knowledge, it answers queries directly from memory rather than executing redundant web searches. This drastically reduces latency and API costs.
          </p>
        </div>
        
        <div style={{ flex:1, display:'flex', gap:20 }}>
          <div style={{ flex:1, padding:20, background:'rgba(255,255,255,0.03)', borderRadius:12, border:'1px dashed rgba(255,255,255,0.1)' }}>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--on-surface-muted)', marginBottom:12 }}>WITHOUT MEMORY</div>
            <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
              <div style={{ display:'flex', justifyContent:'space-between' }}>
                <span style={{ color:'var(--on-surface-var)', fontSize:14 }}>Searches</span>
                <span style={{ fontFamily:'var(--font-mono)', color:'var(--error)' }}>{expSearches}</span>
              </div>
              <div style={{ display:'flex', justifyContent:'space-between' }}>
                <span style={{ color:'var(--on-surface-var)', fontSize:14 }}>Est. Latency</span>
                <span style={{ fontFamily:'var(--font-mono)', color:'var(--error)' }}>{expSearches * 1.5}s</span>
              </div>
            </div>
          </div>
          
          <div style={{ flex:1, padding:20, background:'rgba(99,102,241,0.08)', borderRadius:12, border:'1px solid rgba(99,102,241,0.3)' }}>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--primary)', marginBottom:12, display:'flex', alignItems:'center', gap:6 }}>
              <span style={{ fontSize:14 }}>⚡</span> WITH MEMORY
            </div>
            <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
              <div style={{ display:'flex', justifyContent:'space-between' }}>
                <span style={{ color:'var(--on-surface-var)', fontSize:14 }}>Searches</span>
                <span style={{ fontFamily:'var(--font-mono)', color:'var(--primary)' }}>{actSearches}</span>
              </div>
              <div style={{ display:'flex', justifyContent:'space-between' }}>
                <span style={{ color:'var(--on-surface-var)', fontSize:14 }}>Est. Latency</span>
                <span style={{ fontFamily:'var(--font-mono)', color:'var(--primary)' }}>{actSearches * 1.5}s</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'2fr 1fr', gap:20, marginBottom:24 }}>
        
        {/* Knowledge Growth Chart */}
        <div className="glass" style={{ padding:28 }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:24 }}>
            <div>
              <h2 style={{ fontFamily:'var(--font-headline)', fontSize:18, fontWeight:600 }}>Knowledge Growth</h2>
              <p style={{ color:'var(--on-surface-muted)', fontSize:13, marginTop:4 }}>Cumulative entities and claims assimilated</p>
            </div>
            <span className="chip chip-indigo">+{m?.search_count ?? 0} ingested today</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={growthData}>
              <defs>
                <linearGradient id="ent" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="clm" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#22d3ee" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="month" tick={{ fill:'#908fa0', fontSize:12, fontFamily:'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:'#908fa0', fontSize:11 }} axisLine={false} tickLine={false} tickFormatter={(v)=>v>1000?`${v/1000}k`:v} />
              <Tooltip contentStyle={{ background:'#1b1f2c', border:'1px solid rgba(255,255,255,0.1)', borderRadius:8, fontFamily:'JetBrains Mono', fontSize:13 }} />
              <Area type="monotone" dataKey="entities" stroke="#6366f1" fill="url(#ent)" strokeWidth={2} name="Entities" />
              <Area type="monotone" dataKey="claims" stroke="#22d3ee" fill="url(#clm)" strokeWidth={2} name="Claims" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Cognitive Maturity & Maintenance */}
        <div style={{ display:'flex', flexDirection:'column', gap:20 }}>
          
          <div className="glass" style={{ padding:24, flex:1 }}>
            <h2 style={{ fontFamily:'var(--font-headline)', fontSize:16, fontWeight:600, marginBottom:16 }}>Cognitive Maturity</h2>
            <div style={{ background:'rgba(0,0,0,0.2)', borderRadius:12, padding:16, marginBottom:16 }}>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--primary-dim)', marginBottom:6 }}>CURRENT STAGE</div>
              <div style={{ fontFamily:'var(--font-headline)', fontSize:20, fontWeight:700, color:'var(--primary)' }}>{maturityStage}</div>
            </div>
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}>
              <span style={{ fontSize:13, color:'var(--on-surface-var)' }}>Bootstrap</span>
              <span style={{ fontSize:13, color:'var(--on-surface-var)' }}>Cognitive</span>
            </div>
            <div style={{ height:6, background:'rgba(255,255,255,0.06)', borderRadius:3, overflow:'hidden' }}>
              <div style={{ height:'100%', width:`${progressPercent}%`, background:'linear-gradient(90deg, var(--primary), var(--secondary))', borderRadius:3, transition:'width 1s ease-out' }} />
            </div>
          </div>

          <div className="glass" style={{ padding:24, flex:1 }}>
            <h2 style={{ fontFamily:'var(--font-headline)', fontSize:16, fontWeight:600, marginBottom:16 }}>Knowledge Maintenance</h2>
            <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <span style={{ fontSize:13, color:'var(--on-surface-muted)' }}>Contradictions Detected</span>
                <span style={{ fontFamily:'var(--font-mono)', fontWeight:600, color:'var(--secondary-dim)' }}>{m?.contradictions_detected ?? '—'}</span>
              </div>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <span style={{ fontSize:13, color:'var(--on-surface-muted)' }}>Stale Claims Refreshed</span>
                <span style={{ fontFamily:'var(--font-mono)', fontWeight:600, color:'var(--tertiary)' }}>{m?.stale_refreshed ?? '—'}</span>
              </div>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <span style={{ fontSize:13, color:'var(--on-surface-muted)' }}>Duplicate Entities Merged</span>
                <span style={{ fontFamily:'var(--font-mono)', fontWeight:600, color:'var(--primary-dim)' }}>{m?.duplicates_merged ?? '—'}</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
