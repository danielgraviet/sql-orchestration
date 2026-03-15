import { CompetitionResult } from '../types'

interface Props {
  result: CompetitionResult
  visible: boolean
}

function estimateCost(numAgents: number): string {
  const inputTokens = numAgents * 920
  const outputTokens = numAgents * 200
  const cost = (inputTokens / 1_000_000) * 3.0 + (outputTokens / 1_000_000) * 15.0
  return `$${cost.toFixed(4)}`
}

export default function MetricsBar({ result, visible }: Props) {
  if (!visible) return null

  const { sandboxes_run, success_count, p50_latency_ms } = result
  const successRate = sandboxes_run > 0
    ? `${success_count}/${sandboxes_run}`
    : '—'
  const p50 = p50_latency_ms != null ? `${p50_latency_ms.toFixed(2)}ms` : '—'
  const cost = estimateCost(sandboxes_run)

  const metrics = [
    { label: 'sandboxes run', value: String(sandboxes_run) },
    { label: 'success rate', value: successRate },
    { label: 'P50 latency', value: p50 },
    { label: 'est. API cost', value: cost },
  ]

  return (
    <div className="mt-6 border border-[#2a2a2a] rounded-lg bg-[#141414]">
      <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-y sm:divide-y-0 divide-[#2a2a2a]">
        {metrics.map(({ label, value }) => (
          <div key={label} className="px-5 py-4 text-center">
            <p className="text-xs uppercase tracking-widest text-gray-500 mb-1">{label}</p>
            <p className="text-lg font-mono font-medium text-gray-100">{value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
