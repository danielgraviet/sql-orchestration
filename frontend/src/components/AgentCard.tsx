import { AgentCardData } from '../types'

interface Props {
  card: AgentCardData
}

export default function AgentCard({ card }: Props) {
  const { state, role, result } = card

  if (state === 'idle') {
    return (
      <div className="rounded-xl border border-[#2a2a2a] bg-[#141414] p-4 h-32 animate-pulse" />
    )
  }

  if (state === 'booting') {
    return (
      <div className="rounded-xl border border-[#2a2a2a] bg-[#141414] p-4 h-32 flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
          <span className="text-xs font-medium text-gray-400">{role ?? 'Agent'}</span>
        </div>
        <p className="text-xs text-gray-600">booting sandbox…</p>
      </div>
    )
  }

  const passed = state === 'passed'

  return (
    <div className={`rounded-xl border p-4 h-32 flex flex-col justify-between ${
      passed ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'
    }`}>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${passed ? 'bg-green-400' : 'bg-red-400'}`} />
        <span className="text-xs font-medium text-gray-300">{role ?? 'Agent'}</span>
      </div>

      {passed && result ? (
        <div className="flex gap-4 text-xs text-gray-400">
          <span>score <span className="text-gray-200 font-medium">{result.score.toFixed(1)}</span></span>
          {result.latency_ms != null && (
            <span>latency <span className="text-gray-200 font-medium">{result.latency_ms.toFixed(1)}ms</span></span>
          )}
          {result.rows_returned != null && (
            <span>rows <span className="text-gray-200 font-medium">{result.rows_returned}</span></span>
          )}
        </div>
      ) : (
        <p className="text-xs text-red-400 truncate">
          {result?.error?.replace('FAILED_', '') ?? 'failed'}
        </p>
      )}
    </div>
  )
}