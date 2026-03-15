import { CompetitionResult } from '../types'

interface Props {
  result: CompetitionResult
  visible: boolean
}

export default function WinnerCard({ result, visible }: Props) {
  const { winner, winner_sql } = result

  return (
    <div
      className={`
        transition-all duration-500 ease-out overflow-hidden
        ${visible ? 'max-h-[800px] opacity-100 translate-y-0' : 'max-h-0 opacity-0 translate-y-4'}
      `}
    >
      <div className="mt-8 border border-amber-500/40 rounded-lg bg-[#141414] shadow-[0_0_30px_rgba(245,158,11,0.1)]">
        <div className="p-5 border-b border-[#2a2a2a]">
          <div className="flex items-center gap-3 mb-1">
            <span className="text-amber-400 text-xl" aria-label="winner">★</span>
            <h2 className="text-lg font-semibold text-amber-400">Winner</h2>
            <span className="ml-auto text-xs font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded">
              score {winner.score.toFixed(1)}
            </span>
          </div>
          <p className="text-xl font-medium text-gray-100">{winner.role ?? winner.sandbox_id}</p>
          {winner.latency_ms != null && (
            <p className="text-sm text-gray-400 mt-1">
              {winner.latency_ms.toFixed(2)}ms latency
              {winner.rows_returned != null && ` · ${winner.rows_returned} rows`}
            </p>
          )}
        </div>

        {winner.rationale && (
          <div className="p-5 border-b border-[#2a2a2a]">
            <p className="text-xs uppercase tracking-widest text-gray-500 mb-2">Rationale</p>
            <p className="text-sm text-gray-300 leading-relaxed">{winner.rationale}</p>
          </div>
        )}

        {winner_sql && (
          <div className="p-5">
            <p className="text-xs uppercase tracking-widest text-gray-500 mb-2">Winning SQL</p>
            <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] overflow-x-auto">
              <pre className="font-mono text-xs text-green-300 p-4 leading-relaxed whitespace-pre">
                {winner_sql}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
