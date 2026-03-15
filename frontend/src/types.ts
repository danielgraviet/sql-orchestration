export type AgentState = 'idle' | 'booting' | 'passed' | 'failed'

export interface AgentResult {
  sandbox_id: string
  role: string | null
  passed: boolean
  score: number
  latency_ms: number | null
  explain_cost: number | null
  rows_returned: number | null
  error: string | null
  sql_length?: number | null
}

export interface WinnerResult extends AgentResult {
  rationale: string | null
}

export interface CompetitionResult {
  task: string
  winner: WinnerResult
  winner_sql: string | null
  all_results: AgentResult[]
  sandboxes_run: number
  success_count: number
  failed_count: number
  p50_latency_ms: number | null
  best_score: number
}

export interface SSEEvent {
  type: string
  sandbox_id: string | null
  role: string | null
  result: AgentResult | null
  total: number | null
  completed: number | null
  timestamp: number
}

export interface AgentCardData {
  sandbox_id: string | null
  role: string | null
  state: AgentState
  result: AgentResult | null
}
