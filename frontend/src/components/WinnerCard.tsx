import { CompetitionResult } from '../types'

interface Props {
  result: CompetitionResult
  visible: boolean
}

export default function WinnerCard({ result, visible }: Props) {
  const { winner, winner_sql } = result

  return (
    <div className={`mt-8 rounded-xl border border-yellow-500/30 bg-yellow-500/5 p-6 transition-all duration-300 ${
      visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
    }`}>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-yellow-400 text-sm">★</span>
        <h2 className="text-sm font-semibold text-gray-200">Winner: {winner.role ?? winner.sandbox_id}</h2>
        <span className="ml-auto text-xs text-gray-500">score {winner.score.toFixed(1)}</span>
      </div>

      {winner.rationale && (
        <p className="text-xs text-gray-400 mb-4 leading-relaxed">{winner.rationale}</p>
      )}

      {winner_sql && (
        <pre className="text-xs text-gray-300 bg-[#0a0a0a] border border-[#2a2a2a] rounded-lg p-4 overflow-x-auto whitespace-pre-wrap">
          {winner_sql}
        </pre>
      )}
    </div>
  )
}
