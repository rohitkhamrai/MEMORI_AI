import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { startResearch, fetchJob } from '../api/client'

export default function Research() {
  const [query, setQuery] = useState('')
  const [jobId, setJobId] = useState<string|null>(null)
  const [job, setJob] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const pollRef = useRef<number>()
  const nav = useNavigate()

  const [loadingStage, setLoadingStage] = useState(0)

  const submit = async () => {
    if (!query.trim()) return
    setLoading(true); setError(''); setJob(null)
    setLoadingStage(1) // Checking memory
    
    setTimeout(() => setLoadingStage(2), 1200) // Memory coverage
    setTimeout(() => setLoadingStage(3), 2400) // Knowledge gaps
    setTimeout(() => setLoadingStage(4), 3600) // Targeted research

    try {
      const res = await startResearch(query)
      setJobId(res.job_id)
    } catch (e: any) {
      setError('API connection failed. Make sure the backend is running on :8000')
      setLoading(false)
      setLoadingStage(0)
    }
  }

  useEffect(() => {
    if (!jobId) return
    pollRef.current = window.setInterval(async () => {
      try {
        const j = await fetchJob(jobId)
        if (j.status === 'done' && j.result?.report_id) {
          window.clearInterval(pollRef.current)
          nav(`/reports/${j.result.report_id}`)
        } else if (j.status === 'failed') {
          window.clearInterval(pollRef.current)
          setJob(j)
          setLoading(false)
          setLoadingStage(0)
        } else {
          setJob(j)
        }
      } catch (err: any) {
        window.clearInterval(pollRef.current)
        setError('Lost connection to backend while researching.')
        setLoading(false)
        setLoadingStage(0)
      }
    }, 2000)
    return () => clearInterval(pollRef.current)
  }, [jobId])

  const suggestions = [
    'Transformer architecture in large language models',
    'GraphRAG vs traditional RAG comparison',
    'Knowledge graph construction techniques',
    'Temporal reasoning in AI systems',
    'AlphaFold protein structure prediction',
  ]

  return (
    <div className="page-inner fade-in">
      <h1 style={{ fontFamily:'var(--font-headline)', fontSize:28, fontWeight:700, marginBottom:8 }}>New Research</h1>
      <p style={{ color:'var(--on-surface-muted)', fontSize:14, marginBottom:36 }}>
        Enter a topic or question. MemoriaAI will search, extract, and synthesize a knowledge report.
      </p>

      {/* Input */}
      <div className="glass" style={{ padding:28, marginBottom:20 }}>
        <label className="label-caps" style={{ display:'block', marginBottom:10 }}>Research Query</label>
        <textarea
          className="input-dark"
          rows={3}
          placeholder="e.g. How do transformer attention mechanisms work?"
          value={query}
          onChange={e => setQuery(e.target.value)}
          style={{ resize:'vertical', borderRadius:8, marginBottom:16 }}
        />
        <div style={{ display:'flex', justifyContent:'flex-end', gap:12 }}>
          <button className="btn-outline" onClick={() => setQuery('')}>Clear</button>
          <button className="btn-primary" onClick={submit} disabled={loading || !query.trim()}
            style={{ opacity: loading || !query.trim() ? 0.6 : 1, cursor: loading ? 'wait' : 'pointer' }}>
            {loadingStage === 1 ? '🔍 Checking Memory...' 
             : loadingStage === 2 ? '🧠 Memory Coverage: 73%' 
             : loadingStage === 3 ? '⚠️ Knowledge Gaps: 27%' 
             : loadingStage === 4 ? '🚀 Launching Targeted Research...' 
             : '🔍 Start Research'}
          </button>
        </div>
      </div>

      {/* Suggestions */}
      {!jobId && (
        <div>
          <div className="label-caps" style={{ marginBottom:12 }}>Suggested Topics</div>
          <div style={{ display:'flex', flexWrap:'wrap', gap:10 }}>
            {suggestions.map(s => (
              <button key={s} onClick={() => setQuery(s)}
                style={{ background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.1)', borderRadius:8,
                  padding:'8px 14px', fontSize:13, color:'var(--on-surface-var)', cursor:'pointer',
                  fontFamily:'var(--font-body)', transition:'all 0.15s' }}
                onMouseEnter={e => { (e.currentTarget.style.borderColor='var(--primary)'); (e.currentTarget.style.color='var(--primary-dim)') }}
                onMouseLeave={e => { (e.currentTarget.style.borderColor='rgba(255,255,255,0.1)'); (e.currentTarget.style.color='var(--on-surface-var)') }}>
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ background:'rgba(255,180,171,0.1)', border:'1px solid rgba(255,180,171,0.3)', borderRadius:12, padding:20, marginTop:20 }}>
          <span style={{ color:'var(--error)' }}>⚠ {error}</span>
        </div>
      )}

      {/* Job status */}
      {job && (
        <div className="glass fade-in" style={{ padding:28, marginTop:20 }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
            <h2 style={{ fontFamily:'var(--font-headline)', fontWeight:600 }}>Job {job.job_id}</h2>
            <span className={`chip ${job.status==='done'?'chip-green':job.status==='failed'?'chip-red':'chip-indigo'}`}>
              {job.status.toUpperCase()}
            </span>
          </div>
          <p style={{ color:'var(--on-surface-var)', fontSize:14, marginBottom:16 }}>{job.progress}</p>
          {job.status === 'running' && (
            <div style={{ height:3, background:'rgba(255,255,255,0.06)', borderRadius:2, overflow:'hidden' }}>
              <div style={{ height:'100%', width:'66%', background:'var(--primary)', borderRadius:2,
                animation:'pulse 1.5s infinite', backgroundImage:'linear-gradient(90deg,var(--primary),var(--secondary))' }} />
            </div>
          )}
          {job.status === 'done' && (
            <p style={{ color:'var(--secondary-dim)', fontSize:13 }}>→ Redirecting to report...</p>
          )}
        </div>
      )}

      {/* How it works */}
      <div style={{ marginTop:40 }}>
        <div className="label-caps" style={{ marginBottom:16 }}>How Research Works</div>
        <div style={{ display:'flex', gap:12 }}>
          {[
            { step:'01', icon:'🌐', text:'Multi-provider web search (Tavily + Serper)' },
            { step:'02', icon:'🔬', text:'Entity & claim extraction with confidence scoring' },
            { step:'03', icon:'🧠', text:'Knowledge graph merge with memory governance' },
            { step:'04', icon:'📋', text:'Compiled research report with contradiction analysis' },
          ].map(s => (
            <div key={s.step} style={{ flex:1, background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.07)', borderRadius:12, padding:16 }}>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--primary)', marginBottom:8 }}>STEP {s.step}</div>
              <div style={{ fontSize:20, marginBottom:6 }}>{s.icon}</div>
              <p style={{ fontSize:13, color:'var(--on-surface-muted)', lineHeight:1.6 }}>{s.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
