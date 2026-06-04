import axios from 'axios'

// In production (when built), this should fall back to an absolute URL or proxy
// depending on Vercel/Netlify setup.
const api = axios.create({ 
  baseURL: import.meta.env.VITE_API_URL ?? '/api', timeout: 120000 
})

export interface Metrics {
  query_count: number; search_count: number; memory_hits: number; memory_misses: number;
  claims_accepted: number; claims_rejected: number; contradiction_count: number;
  refresh_count: number; average_latency_ms: number; cache_hit_rate: number;
  node_count: number; relationship_count: number; community_count: number;
  hub_node_count: number; stale_claims: number; refresh_queue_size: number;
  // Evolution fields
  memory_reuse_rate: number; searches_avoided: number; time_saved_hours: number;
  token_savings: number; learning_efficiency: number; stale_refreshed: number;
  contradictions_resolved: number; duplicates_merged: number;
  knowledge_reused: number; knowledge_new: number;
  maturity_stage?: string; maturity_score?: number;
  history?: { month: string, entities: number, claims: number, communities: number, reuse_rate: number }[];
}

export interface GraphData {
  nodes: { id:string; name:string; type:string; importance:number; community:number; degree:number; description:string }[];
  edges: { source:string; target:string; predicate:string; confidence:number }[];
  communities: { id:number; name?:string; color:string; size:number }[];
  hub_nodes: string[];
}

export interface Job { job_id:string; query:string; status:string; progress:string; created_at:string; result:any }
export interface Report { id:string; query:string; created_at:string; report_json?:any }

export const fetchHealth   = () => api.get('/health').then(r => r.data)
export const fetchMetrics  = () => api.get<Metrics>('/metrics').then(r => r.data)
export const fetchGraph    = () => api.get<GraphData>('/graph').then(r => r.data)
export const fetchReports  = () => api.get<{reports:Report[]; count:number}>('/reports').then(r => r.data)
export const fetchReport   = (id:string) => api.get<Report>(`/reports/${id}`).then(r => r.data)
export const fetchJob      = (id:string) => api.get<Job>(`/jobs/${id}`).then(r => r.data)
export const startResearch = (query:string) => api.post<{job_id:string; status:string}>('/research', {query}).then(r => r.data)
export const fetchEntities = () => api.get('/memory/entities').then(r => r.data)
export const fetchClaims   = () => api.get('/memory/claims').then(r => r.data)
export const fetchContradictions = () => api.get('/memory/contradictions').then(r => r.data)
