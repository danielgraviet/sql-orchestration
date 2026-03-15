import { AgentCardData } from '../types'

interface Props {
  card: AgentCardData
}

function Skeleton() {
  return (
    <div className="space-y-3 p-4">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-[#2a2a2a] animate-pulse" />
        <div className="h-4 bg-[#2a2a2a] rounded animate-pulse flex-1" />
      </div>
      <div className="h-3 bg-[#2a2a2a] rounded animate-pulse w-3/4" />
      <div className="h-3 bg-[#2a2a2a] rounded animate-pulse w-1/2" />
    </div>
  )
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5 text-blue-400"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}

function sqlPreview(sql: string | null | undefined): string {
  if (!sql) return ''
  return sql.trim().split('\n').slice(0, 3).join('\n')
}

export default function AgentCard({ card }: Props) {
  const { state, role, result } = card

  return (
    <div className="bg-[#141414] border border-[#2a2a2a] rounded-lg overflow-hidden transition-all duration-300">
      {state === 'idle' && <Skeleton />}

      {state === 'booting' && (
        <div className="p-4 space-y-2">
          <div className="flex items-center gap-3">
            <Spinner />
            <span className="font-medium text-gray-200 truncate">{role ?? 'Agent'}</span>
          </div>
          <p className="text-sm text-gray-500">Booting sandbox...</p>
        </div>
      )}

      {state === 'passed' && result && (
        <div className="p-4 space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-green-500 text-lg" aria-label="passed">✓</span>
            <span className="font-medium text-gray-200 truncate flex-1">{role ?? result.sandbox_id}</span>
            <span className="text-xs font-mono bg-green-500/10 text-green-400 border border-green-500/20 px-2 py-0.5 rounded">
              {result.score.toFixed(1)}
            </span>
          </div>
          {result.latency_ms != null && (
            <p className="text-xs text-gray-500">
              {result.latency_ms.toFixed(2)}ms
              {result.rows_returned != null && ` · ${result.rows_returned} rows`}
            </p>
          )}
          {result.sql_length != null && (
            <pre className="font-mono text-xs text-gray-400 bg-[#0a0a0a] rounded p-2 overflow-hidden leading-relaxed line-clamp-3">
              {sqlPreview(`-- ${role}\nSELECT ... (${result.sql_length} chars)`)}
            </pre>
          )}
        </div>
      )}

      {state === 'failed' && (
        <div className="p-4 space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-red-500 text-lg" aria-label="failed">✗</span>
            <span className="font-medium text-gray-200 truncate">{role ?? result?.sandbox_id ?? 'Agent'}</span>
            <span className="text-xs font-mono bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded">
              0
            </span>
          </div>
          <p className="text-xs text-red-400 truncate">
            {result?.error?.replace('FAILED_', '') ?? 'Unknown error'}
          </p>
        </div>
      )}
    </div>
  )
}
