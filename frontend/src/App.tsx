import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Landing from './pages/Landing'
import KnowledgeEvolution from './pages/KnowledgeEvolution'
import SystemTelemetry from './pages/SystemTelemetry'
import Research from './pages/Research'
import Reports from './pages/Reports'
import ReportDetail from './pages/ReportDetail'
import GraphExplorer from './pages/GraphExplorer'
import MemoryExplorer from './pages/MemoryExplorer'

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">{children}</div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout><KnowledgeEvolution /></AppLayout>} />
        <Route path="/telemetry" element={<AppLayout><SystemTelemetry /></AppLayout>} />
        <Route path="/research" element={<AppLayout><Research /></AppLayout>} />
        <Route path="/reports" element={<AppLayout><Reports /></AppLayout>} />
        <Route path="/reports/:id" element={<AppLayout><ReportDetail /></AppLayout>} />
        <Route path="/graph" element={
          <div className="app-layout">
            <Sidebar />
            <div style={{ flex:1, display:'flex', overflow:'hidden' }}><GraphExplorer /></div>
          </div>
        } />
        <Route path="/memory" element={<AppLayout><MemoryExplorer /></AppLayout>} />
        <Route path="/observability" element={<Navigate to="/telemetry" replace />} />
        <Route path="/dashboard" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
