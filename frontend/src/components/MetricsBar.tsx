import { CompetitionResult } from '../types'

interface Props {
  result: CompetitionResult
  visible: boolean
}

function estimateCost(numAgents: number): string {
  const cost = (numAgents * 920 / 1_000_000) * 3.0 + (numAgents * 200 / 1_000_000) * 15.0
  return cost.toFixed(4)
}

export default function MetricsBar({ result, visible }: Props) {
  const { sandboxes_run, success_count, p50_latency_ms } = result
  const cost = estimateCost(sandboxes_run)

  const metrics = [
    { label: 'Sandboxes run', value: String(sandboxes_run) },
    { label: 'Success rate', value: `${success_count}/${sandboxes_run}` },
    { label: 'P50 latency', value: p50_latency_ms != null ? `${p50_latency_ms.toFixed(1)}ms` : '—' },
    { label: 'Est. API cost', value: `$${cost}` },
  ]

  return (
    <div className={`mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 transition-all duration-300 ${
      visible ? 'opacity-100' : 'opacity-0'
    }`}>
      {metrics.map(m => (
        <div key={m.label} className="rounded-lg border border-[#2a2a2a] bg-[#141414] px-4 py-3">
          <p className="text-xs text-gray-500 mb-1">{m.label}</p>
          <p className="text-sm font-medium text-gray-200">{m.value}</p>
        </div>
      ))}
    </div>
  )
}
