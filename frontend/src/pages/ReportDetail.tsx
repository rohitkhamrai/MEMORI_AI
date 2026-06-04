import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchReport } from '../api/client'

export default function ReportDetail() {
  const { id } = useParams<{id:string}>()
  const [report, setReport] = useState<any>(null)
  const [tab, setTab] = useState<'summary'|'claims'|'contradictions'|'gaps'>('summary')
  const nav = useNavigate()

  useEffect(() => {
    if (id) fetchReport(id).then(setReport).catch(()=>{})
  }, [id])

  if (!report) return (
    <div className="page-inner" style={{ textAlign:'center', paddingTop:80 }}>
      <div style={{ fontSize:36, marginBottom:12 }}>⏳</div>
      <p style={{ color:'var(--on-surface-muted)' }}>Loading report...</p>
    </div>
  )

  const r = report.report_json
  const tabs = [
    { key:'summary', label:'Summary' },
    { key:'claims', label:`Claims (${r?.factual_triple_trace?.records?.length ?? 0})` },
    { key:'contradictions', label:`Contradictions (${r?.divergence_contradiction_matrix?.contradictions?.length ?? 0})` },
    { key:'gaps', label:`Knowledge Gaps (${r?.knowledge_gap_footprint?.missing_structures?.length ?? 0})` },
  ]

  return (
    <div className="page-inner fade-in">
      <button onClick={() => nav('/reports')} style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--on-surface-muted)', background:'none', border:'none', cursor:'pointer', marginBottom:20 }}>
        ← Back to Reports
      </button>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 280px', gap:24 }}>
        <div>
          {/* Header */}
          <div style={{ marginBottom:24 }}>
            <div className="label-caps" style={{ marginBottom:6 }}>REPORT · {report.id}</div>
            <h1 style={{ fontFamily:'var(--font-headline)', fontSize:26, fontWeight:700, lineHeight:1.3, marginBottom:8 }}>{r?.title ?? report.query}</h1>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--on-surface-muted)' }}>{new Date(report.created_at).toLocaleString()}</div>
          </div>

          {/* Tabs */}
          <div style={{ display:'flex', gap:4, marginBottom:20, borderBottom:'1px solid rgba(255,255,255,0.06)', paddingBottom:0 }}>
            {tabs.map(t => (
              <button key={t.key} onClick={() => setTab(t.key as any)}
                style={{
                  background:'none', border:'none', cursor:'pointer', padding:'10px 16px',
                  fontFamily:'var(--font-mono)', fontSize:12,
                  color: tab===t.key ? 'var(--primary-dim)' : 'var(--on-surface-muted)',
                  borderBottom: tab===t.key ? '2px solid var(--primary)' : '2px solid transparent',
                  transition:'all 0.15s'
                }}>{t.label}</button>
            ))}
          </div>

          {/* Tab content */}
          {tab === 'summary' && (
            <div className="glass" style={{ padding:24 }}>
              <h3 style={{ fontFamily:'var(--font-headline)', fontWeight:600, marginBottom:16 }}>Key Axioms</h3>
              {r?.executive_intelligence_matrix?.axioms?.map((a:string, i:number) => (
                <div key={i} style={{ display:'flex', gap:12, marginBottom:10, padding:'10px 14px', background:'rgba(99,102,241,0.06)', borderRadius:8, borderLeft:'3px solid var(--primary)' }}>
                  <span style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--primary)', minWidth:24 }}>{String(i+1).padStart(2,'0')}</span>
                  <p style={{ fontSize:14, color:'var(--on-surface-var)', lineHeight:1.6 }}>{a}</p>
                </div>
              ))}
              <h3 style={{ fontFamily:'var(--font-headline)', fontWeight:600, marginBottom:16, marginTop:24 }}>Fresh Variables</h3>
              <div style={{ display:'flex', flexWrap:'wrap', gap:8 }}>
                {r?.executive_intelligence_matrix?.fresh_variables?.map((v:string, i:number) => (
                  <span key={i} className="chip chip-cyan">{v}</span>
                ))}
                {!r?.executive_intelligence_matrix?.fresh_variables?.length && <span style={{ color:'var(--on-surface-muted)', fontSize:13 }}>None found</span>}
              </div>
            </div>
          )}
          {tab === 'claims' && (
            <div className="glass" style={{ padding:8 }}>
              <table className="data-table">
                <thead><tr><th>Source</th><th>Predicate</th><th>Target</th><th>Conf.</th></tr></thead>
                <tbody>
                  {r?.factual_triple_trace?.records?.map((rec:any, i:number) => (
                    <tr key={i}>
                      <td style={{ color:'var(--primary-dim)' }}>{rec.source_name}</td>
                      <td><span className="chip chip-indigo">{rec.predicate}</span></td>
                      <td style={{ color:'var(--secondary-dim)' }}>{rec.target_name}</td>
                      <td style={{ fontFamily:'var(--font-mono)', fontSize:12 }}>{(rec.confidence*100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {tab === 'contradictions' && (
            <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
              {r?.divergence_contradiction_matrix?.contradictions?.map((c:any, i:number) => (
                <div key={i} className="glass" style={{ padding:20, borderLeft:'3px solid var(--error)' }}>
                  <div style={{ fontFamily:'var(--font-headline)', fontWeight:600, marginBottom:8, color:'var(--error)' }}>⚠ {c.entity_or_relation}</div>
                  <p style={{ fontSize:13, color:'var(--on-surface-muted)', marginBottom:8 }}>{c.contradiction_summary}</p>
                  <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
                    {c.conflicting_sources?.map((s:string, j:number) => <span key={j} className="chip chip-red">{s}</span>)}
                  </div>
                </div>
              ))}
            </div>
          )}
          {tab === 'gaps' && (
            <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
              {r?.knowledge_gap_footprint?.missing_structures?.map((g:any, i:number) => (
                <div key={i} className="glass" style={{ padding:18, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <div>
                    <div style={{ fontFamily:'var(--font-body)', fontWeight:600, marginBottom:4 }}>{g.missing_entity}</div>
                    <p style={{ fontSize:13, color:'var(--on-surface-muted)' }}>{g.context}</p>
                  </div>
                  <span className={`chip ${g.priority==='HIGH'?'chip-red':g.priority==='MEDIUM'?'chip-amber':'chip-green'}`}>{g.priority}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar meta */}
        <div>
          <div className="glass" style={{ padding:20, marginBottom:16 }}>
            <div className="label-caps" style={{ marginBottom:14 }}>Research Metadata</div>
            {[
              { k:'Report ID', v: report.id },
              { k:'Query', v: report.query.length > 40 ? report.query.slice(0,40)+'...' : report.query },
              { k:'Created', v: new Date(report.created_at).toLocaleDateString() },
              { k:'Claims', v: r?.factual_triple_trace?.records?.length ?? 0 },
              { k:'Contradictions', v: r?.divergence_contradiction_matrix?.contradictions?.length ?? 0 },
              { k:'Knowledge Gaps', v: r?.knowledge_gap_footprint?.missing_structures?.length ?? 0 },
              { k:'Memory Coverage', v: r?.memory_coverage !== undefined ? `${r.memory_coverage}%` : 'N/A' },
            ].map(({k,v}) => (
              <div key={k} style={{ display:'flex', justifyContent:'space-between', padding:'8px 0', borderBottom:'1px solid rgba(255,255,255,0.04)', fontSize:13 }}>
                <span style={{ color:'var(--on-surface-muted)', fontFamily:'var(--font-mono)', fontSize:11 }}>{k}</span>
                <span style={{ color:'var(--on-surface)', fontWeight:600, maxWidth:140, textAlign:'right' }}>{v}</span>
              </div>
            ))}
          </div>
          <button className="btn-outline" style={{ width:'100%' }} onClick={() => nav('/research')}>+ New Research</button>
        </div>
      </div>
    </div>
  )
}
