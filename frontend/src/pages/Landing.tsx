import { useNavigate } from 'react-router-dom'
import { useEffect, useRef } from 'react'

export default function Landing() {
  const nav = useNavigate()
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current!
    const ctx = canvas.getContext('2d')!
    canvas.width = canvas.offsetWidth
    canvas.height = canvas.offsetHeight

    const nodes = Array.from({length:18}, (_, i) => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random()-0.5)*0.4,
      vy: (Math.random()-0.5)*0.4,
      r: Math.random()*4+2,
      color: i%3===0 ? '#6366f1' : i%3===1 ? '#22d3ee' : '#a78bfa'
    }))

    let frame: number
    function draw() {
      ctx.clearRect(0,0,canvas.width,canvas.height)
      // Edges
      nodes.forEach((a,i) => nodes.slice(i+1).forEach(b => {
        const d = Math.hypot(a.x-b.x, a.y-b.y)
        if (d < 160) {
          ctx.beginPath()
          ctx.strokeStyle = `rgba(99,102,241,${(1-d/160)*0.3})`
          ctx.lineWidth = 0.8
          ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke()
        }
      }))
      // Nodes
      nodes.forEach(n => {
        const g = ctx.createRadialGradient(n.x,n.y,0,n.x,n.y,n.r*3)
        g.addColorStop(0, n.color+'99'); g.addColorStop(1, 'transparent')
        ctx.beginPath(); ctx.arc(n.x,n.y,n.r*3,0,Math.PI*2)
        ctx.fillStyle=g; ctx.fill()
        ctx.beginPath(); ctx.arc(n.x,n.y,n.r,0,Math.PI*2)
        ctx.fillStyle=n.color; ctx.fill()
        // Move
        n.x+=n.vx; n.y+=n.vy
        if(n.x<0||n.x>canvas.width) n.vx*=-1
        if(n.y<0||n.y>canvas.height) n.vy*=-1
      })
      frame = requestAnimationFrame(draw)
    }
    draw()
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <div style={{ minHeight:'100vh', background:'var(--bg-base)', display:'flex', flexDirection:'column' }}>
      {/* Nav */}
      <header style={{
        position:'sticky', top:0, zIndex:50,
        background:'rgba(10,14,26,0.8)', backdropFilter:'blur(16px)',
        borderBottom:'1px solid rgba(255,255,255,0.07)',
        display:'flex', alignItems:'center', justifyContent:'space-between',
        padding:'0 48px', height:64
      }}>
        <div style={{ fontFamily:'var(--font-headline)', fontWeight:700, fontSize:18, color:'var(--primary-dim)', display:'flex', alignItems:'center', gap:8 }}>
          🧠 MemoriaAI
        </div>
        <div style={{ display:'flex', gap:32 }}>
          {['Features','How It Works','Pricing','Docs'].map(l => (
            <span key={l} style={{ color:'var(--on-surface-var)', fontSize:14, cursor:'pointer', transition:'color 0.15s' }}
              onMouseEnter={e=>(e.currentTarget.style.color='var(--on-surface)')}
              onMouseLeave={e=>(e.currentTarget.style.color='var(--on-surface-var)')}>{l}</span>
          ))}
        </div>
        <button className="btn-primary" onClick={() => nav('/dashboard')}>Get Started</button>
      </header>

      {/* Hero */}
      <section style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'80px 48px 48px', textAlign:'center', position:'relative' }}>
        <div className="chip chip-indigo" style={{ marginBottom:20, fontSize:12 }}>✦ AI KNOWLEDGE GRAPH RESEARCH ENGINE</div>
        <h1 style={{ fontFamily:'var(--font-headline)', fontSize:'clamp(40px,5vw,72px)', fontWeight:700, lineHeight:1.08, letterSpacing:'-0.03em', marginBottom:20 }}>
          Your Research.<br/>
          <span className="gradient-text">Remembered. Reasoned.</span>
        </h1>
        <p style={{ maxWidth:560, fontSize:18, color:'var(--on-surface-var)', lineHeight:1.7, marginBottom:40 }}>
          An AI knowledge graph that learns and evolves alongside your research. Hybrid retrieval, temporal decay, cognitive routing — all in one engine.
        </p>
        <div style={{ display:'flex', gap:16, marginBottom:64 }}>
          <button className="btn-primary" style={{ fontSize:16, padding:'14px 32px' }} onClick={() => nav('/dashboard')}>Start Researching</button>
          <button className="btn-outline" style={{ fontSize:16, padding:'14px 32px' }} onClick={() => nav('/graph')}>View Demo Graph</button>
        </div>

        {/* Canvas */}
        <div style={{ width:'100%', maxWidth:900, height:360, borderRadius:24, overflow:'hidden', position:'relative', border:'1px solid rgba(255,255,255,0.08)', background:'rgba(255,255,255,0.02)' }}>
          <canvas ref={canvasRef} style={{ width:'100%', height:'100%' }} />
          <div style={{ position:'absolute', bottom:16, left:'50%', transform:'translateX(-50%)', fontFamily:'var(--font-mono)', fontSize:11, color:'var(--on-surface-muted)', letterSpacing:'0.1em' }}>
            LIVE KNOWLEDGE GRAPH SIMULATION
          </div>
        </div>
      </section>

      {/* Features */}
      <section style={{ padding:'80px 48px', background:'var(--bg-surface)' }}>
        <h2 style={{ textAlign:'center', fontFamily:'var(--font-headline)', fontSize:36, fontWeight:700, marginBottom:12 }}>Architected for Deep Context</h2>
        <p style={{ textAlign:'center', color:'var(--on-surface-muted)', marginBottom:56, maxWidth:560, margin:'0 auto 56px' }}>
          Cognitive primitives designed to support rigorous academic and professional research workflows.
        </p>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(260px,1fr))', gap:24, maxWidth:1100, margin:'0 auto' }}>
          {[
            { icon:'🔀', title:'Hybrid Retrieval', desc:'Dense vector search + sparse keyword retrieval for unparalleled accuracy.' },
            { icon:'⏳', title:'Temporal Decay', desc:'Intelligently weights recent info while preserving foundational knowledge context.' },
            { icon:'🧭', title:'Cognitive Routing', desc:'Dynamically selects optimal reasoning model based on graph maturity stage.' },
            { icon:'🌐', title:'Multi-Provider Search', desc:'Tavily, Serper, Brave, DDG — aggregated into a unified knowledge graph.' },
            { icon:'💰', title:'Cost Control', desc:'SHA256 claim cache + LLM escalation only at confidence < 0.60.' },
            { icon:'📡', title:'Observability', desc:'Real-time telemetry into retrieval and reasoning for complete transparency.' },
          ].map(f => (
            <div key={f.title} className="glass fade-in" style={{ padding:28 }}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.transform='translateY(-4px)'; (e.currentTarget as HTMLDivElement).style.borderColor='rgba(99,102,241,0.4)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.transform=''; (e.currentTarget as HTMLDivElement).style.borderColor='' }}>
              <div style={{ fontSize:28, marginBottom:12 }}>{f.icon}</div>
              <div style={{ fontFamily:'var(--font-headline)', fontWeight:600, fontSize:17, marginBottom:8 }}>{f.title}</div>
              <p style={{ color:'var(--on-surface-muted)', fontSize:14, lineHeight:1.6 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding:'28px 48px', borderTop:'1px solid rgba(255,255,255,0.06)', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <span style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--on-surface-muted)' }}>© 2025 MemoriaAI. All rights reserved.</span>
        <div style={{ display:'flex', gap:24 }}>
          {['Privacy Policy','Terms of Service','GitHub'].map(l => (
            <span key={l} style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--on-surface-muted)', cursor:'pointer' }}>{l}</span>
          ))}
        </div>
      </footer>
    </div>
  )
}
