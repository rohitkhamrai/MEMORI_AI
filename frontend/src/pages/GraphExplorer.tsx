import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import { fetchGraph } from '../api/client'
import type { GraphData } from '../api/client'

export default function GraphExplorer() {
  const cyRef = useRef<HTMLDivElement>(null)
  const cyInstance = useRef<cytoscape.Core|null>(null)
  const [graph, setGraph] = useState<GraphData|null>(null)
  const [selected, setSelected] = useState<any>(null)
  const [mode, setMode] = useState<'neo4j'|'demo'>('demo')

  useEffect(() => {
    fetchGraph().then(g => {
      setGraph(g)
      buildCy(g)
    })
  }, [])

  function buildCy(g: GraphData) {
    if (!cyRef.current) return
    if (cyInstance.current) cyInstance.current.destroy()

    const commColors: Record<number, string> = {}
    g.communities.forEach(c => { commColors[c.id] = c.color })

    const elements = [
      ...g.nodes.map(n => ({
        data: {
          id: n.id, label: n.name, type: n.type,
          importance: n.importance, community: n.community,
          color: commColors[n.community] ?? '#6366f1',
          size: 20 + n.importance * 30,
          isHub: g.hub_nodes.includes(n.id),
          description: n.description
        }
      })),
      ...g.edges.map(e => ({
        data: {
          id: `${e.source}-${e.target}`,
          source: e.source, target: e.target,
          label: e.predicate, confidence: e.confidence
        }
      }))
    ]

    cyInstance.current = cytoscape({
      container: cyRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            'label': 'data(label)',
            'color': '#dfe2f3',
            'font-size': '11px',
            'font-family': 'JetBrains Mono, monospace',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 4,
            'width': 'data(size)',
            'height': 'data(size)',
            'border-width': 2,
            'border-color': 'data(color)',
            'border-opacity': 0.6,
            'background-opacity': 0.9,
          }
        },
        {
          selector: 'node[?isHub]',
          style: {
            'border-width': 3,
            'border-color': '#ffffff',
            'border-opacity': 0.8,
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': 'rgba(99,102,241,0.3)',
            'target-arrow-color': 'rgba(99,102,241,0.5)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '9px',
            'color': 'rgba(200,200,255,0.5)',
            'font-family': 'JetBrains Mono, monospace',
            'text-rotation': 'autorotate',
          }
        },
        {
          selector: ':selected',
          style: {
            'border-color': '#ffffff',
            'border-width': 3,
            'line-color': 'rgba(34,211,238,0.7)',
          }
        }
      ],
      layout: { name: 'cose', animate: true, animationDuration: 800, nodeDimensionsIncludeLabels: true } as any,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    })

    cyInstance.current.on('tap', 'node', (e) => {
      const d = e.target.data()
      setSelected({ name:d.label, type:d.type, importance:d.importance, description:d.description, community:d.community })
    })
    cyInstance.current.on('tap', (e) => {
      if (e.target === cyInstance.current) setSelected(null)
    })
  }

  const maturityStage = graph
    ? graph.nodes.length < 10 ? 'Stage 0: Bootstrap'
      : graph.nodes.length < 30 ? 'Stage 1: Sparse'
      : graph.nodes.length < 100 ? 'Stage 2: Structured'
      : 'Stage 3: Cognitive'
    : '—'

  return (
    <div style={{ display:'flex', flex:1, height:'100%', overflow:'hidden' }}>
      {/* Left panel */}
      <div style={{ width:260, background:'var(--bg-surface-low)', borderRight:'1px solid rgba(255,255,255,0.07)', padding:20, overflowY:'auto' }}>
        <h2 style={{ fontFamily:'var(--font-headline)', fontSize:16, fontWeight:700, marginBottom:16 }}>Graph Explorer</h2>

        <div className="label-caps" style={{ marginBottom:8 }}>Maturity Stage</div>
        <div style={{ marginBottom:20 }}>
          <span className="chip chip-indigo" style={{ fontSize:11 }}>{maturityStage}</span>
        </div>

        <div className="label-caps" style={{ marginBottom:8 }}>Graph Stats</div>
        <div style={{ marginBottom:20 }}>
          {[
            { k:'Nodes', v: graph?.nodes.length ?? '—' },
            { k:'Edges', v: graph?.edges.length ?? '—' },
            { k:'Communities', v: graph?.communities.length ?? '—' },
            { k:'Hub Nodes', v: graph?.hub_nodes.length ?? '—' },
          ].map(({k,v}) => (
            <div key={k} style={{ display:'flex', justifyContent:'space-between', padding:'7px 0', borderBottom:'1px solid rgba(255,255,255,0.04)', fontSize:13 }}>
              <span style={{ color:'var(--on-surface-muted)', fontSize:12 }}>{k}</span>
              <span style={{ fontFamily:'var(--font-headline)', fontWeight:700, color:'var(--on-surface)' }}>{v}</span>
            </div>
          ))}
        </div>

        <div className="label-caps" style={{ marginBottom:8 }}>Communities</div>
        <div style={{ marginBottom:20 }}>
          {graph?.communities.map(c => (
            <div key={c.id} style={{ display:'flex', alignItems:'center', gap:8, padding:'6px 0' }}>
              <div style={{ width:10, height:10, borderRadius:'50%', background:c.color, flexShrink:0 }} />
              <span style={{ fontSize:12, color:'var(--on-surface-var)' }}>{c.name ?? `Community ${c.id}`}</span>
              <span style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--on-surface-muted)', marginLeft:'auto' }}>{c.size}</span>
            </div>
          ))}
        </div>

        {/* Selected node */}
        {selected && (
          <div style={{ background:'rgba(99,102,241,0.08)', border:'1px solid rgba(99,102,241,0.25)', borderRadius:10, padding:14 }}>
            <div className="label-caps" style={{ marginBottom:6, color:'var(--primary)' }}>Selected Node</div>
            <div style={{ fontFamily:'var(--font-headline)', fontWeight:700, fontSize:15, marginBottom:6 }}>{selected.name}</div>
            <div style={{ marginBottom:8 }}><span className="chip chip-indigo" style={{ fontSize:10 }}>{selected.type}</span></div>
            <p style={{ fontSize:12, color:'var(--on-surface-muted)', lineHeight:1.6, marginBottom:8 }}>{selected.description}</p>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--on-surface-muted)' }}>
              Importance: {(selected.importance*10).toFixed(1)} / 10
            </div>
          </div>
        )}
      </div>

      {/* Graph canvas */}
      <div style={{ flex:1, position:'relative' }}>
        <div ref={cyRef} style={{ width:'100%', height:'100%', background:'var(--bg-base)' }} />
        <div style={{ position:'absolute', top:16, right:16, fontFamily:'var(--font-mono)', fontSize:11, color:'var(--on-surface-muted)', background:'rgba(10,14,26,0.8)', padding:'6px 12px', borderRadius:6 }}>
          Click node to inspect · Scroll to zoom
        </div>
      </div>
    </div>
  )
}
