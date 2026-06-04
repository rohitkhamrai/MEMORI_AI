import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchReports } from '../api/client'
import type { Report } from '../api/client'

export default function Reports() {
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const nav = useNavigate()

  useEffect(() => {
    fetchReports().then(d => { setReports(d.reports); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  return (
    <div className="page-inner fade-in">
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:28 }}>
        <div>
          <h1 style={{ fontFamily:'var(--font-headline)', fontSize:28, fontWeight:700 }}>Research Reports</h1>
          <p style={{ color:'var(--on-surface-muted)', fontSize:14, marginTop:4 }}>All compiled research sessions, stored persistently in SQLite.</p>
        </div>
        <button className="btn-primary" onClick={() => nav('/research')}>+ New Research</button>
      </div>

      <div className="glass" style={{ padding:8 }}>
        {loading && (
          <div style={{ padding:40, textAlign:'center', color:'var(--on-surface-muted)', fontFamily:'var(--font-mono)' }}>Loading reports...</div>
        )}
        {!loading && reports.length === 0 && (
          <div style={{ padding:48, textAlign:'center' }}>
            <div style={{ fontSize:40, marginBottom:12 }}>📋</div>
            <p style={{ fontFamily:'var(--font-headline)', fontWeight:600, marginBottom:8 }}>No reports yet</p>
            <p style={{ color:'var(--on-surface-muted)', fontSize:14, marginBottom:20 }}>Run a research sweep to generate your first report.</p>
            <button className="btn-primary" onClick={() => nav('/research')}>Start Researching</button>
          </div>
        )}
        {reports.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Query</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {reports.map(r => (
                <tr key={r.id} style={{ cursor:'pointer' }} onClick={() => nav(`/reports/${r.id}`)}>
                  <td><span className="chip chip-indigo">{r.id}</span></td>
                  <td style={{ maxWidth:400, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', color:'var(--on-surface)' }}>{r.query}</td>
                  <td style={{ fontFamily:'var(--font-mono)', fontSize:12 }}>{new Date(r.created_at).toLocaleString()}</td>
                  <td><span style={{ color:'var(--primary)', fontFamily:'var(--font-mono)', fontSize:12 }}>View →</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
