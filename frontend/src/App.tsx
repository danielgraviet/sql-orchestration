import { useState, useRef, useCallback } from 'react'
import AgentCard from './components/AgentCard'
import ProgressBar from './components/ProgressBar'
import WinnerCard from './components/WinnerCard'
import MetricsBar from './components/MetricsBar'
import { AgentCardData, CompetitionResult, SSEEvent } from './types'

const TOTAL_AGENTS = 5

function makeIdleCards(): AgentCardData[] {
  return Array.from({ length: TOTAL_AGENTS }, (_, i) => ({
    sandbox_id: null,
    role: null,
    state: 'idle' as const,
    result: null,
    _slotIndex: i,
  }))
}

export default function App() {
  const [task, setTask] = useState('Find the top 10 customers by total spend in the last 90 days')
  const [cards, setCards] = useState<AgentCardData[]>(makeIdleCards)
  const [completed, setCompleted] = useState(0)
  const [total, setTotal] = useState(0)
  const [progressVisible, setProgressVisible] = useState(false)
  const [competitionResult, setCompetitionResult] = useState<CompetitionResult | null>(null)
  const [winnerVisible, setWinnerVisible] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const esRef = useRef<EventSource | null>(null)
  const slotMapRef = useRef<Map<string, number>>(new Map())
  const nextSlotRef = useRef(0)

  const resetState = useCallback(() => {
    esRef.current?.close()
    slotMapRef.current = new Map()
    nextSlotRef.current = 0
    setCards(makeIdleCards())
    setCompleted(0)
    setTotal(0)
    setProgressVisible(false)
    setCompetitionResult(null)
    setWinnerVisible(false)
    setError(null)
  }, [])

  const handleSSEEvent = useCallback((raw: string) => {
    let event: SSEEvent
    try {
      event = JSON.parse(raw)
    } catch {
      return
    }

    if (event.type === 'generation_done' && event.total) {
      setTotal(event.total)
      setProgressVisible(true)
    }

    if (event.type === 'sandbox_start' && event.sandbox_id) {
      const slot = nextSlotRef.current % TOTAL_AGENTS
      slotMapRef.current.set(event.sandbox_id, slot)
      nextSlotRef.current++

      setCards(prev => {
        const next = [...prev]
        next[slot] = {
          sandbox_id: event.sandbox_id,
          role: event.role,
          state: 'booting',
          result: null,
        }
        return next
      })
    }

    if (event.type === 'sandbox_done' || event.type === 'sandbox_failed') {
      const slot = slotMapRef.current.get(event.sandbox_id ?? '')
      if (slot === undefined) return

      setCompleted(c => c + 1)
      setCards(prev => {
        const next = [...prev]
        next[slot] = {
          sandbox_id: event.sandbox_id,
          role: event.role,
          state: event.type === 'sandbox_done' ? 'passed' : 'failed',
          result: event.result,
        }
        return next
      })
    }

    if (event.type === 'competition_done' && event.result) {
      const result = event.result as unknown as CompetitionResult
      setCompetitionResult(result)
      setRunning(false)

      const finalResults = result.all_results ?? []
      setCards(prev => prev.map(card => {
        if (!card.sandbox_id) return card
        const final = finalResults.find(r => r.sandbox_id === card.sandbox_id)
        if (!final) return card
        return {
          ...card,
          state: final.passed ? 'passed' : 'failed',
          result: final,
        }
      }))

      setTimeout(() => setWinnerVisible(true), 200)
    }

    if (event.type === 'error') {
      setError((event as unknown as { message: string }).message)
      setRunning(false)
    }
  }, [])

  const startRun = useCallback(async (dryRun: boolean) => {
    if (!task.trim()) return
    resetState()
    setRunning(true)

    try {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: task.trim(), force: false, dry_run: dryRun }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const { run_id } = await res.json() as { run_id: string }

      const es = new EventSource(`/api/run/${run_id}/stream`)
      esRef.current = es

      es.onmessage = (e) => handleSSEEvent(e.data)
      es.onerror = () => {
        es.close()
        setRunning(false)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setRunning(false)
    }
  }, [task, resetState, handleSSEEvent])

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-gray-200">
      <div className="max-w-5xl mx-auto px-4 py-10">
        <header className="mb-10">
          <h1 className="text-2xl font-semibold tracking-tight text-gray-100">
            SQL Agent Competition
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Five agents compete to write the best SQL for your task
          </p>
        </header>

        <div className="flex gap-3 mb-8">
          <input
            type="text"
            value={task}
            onChange={e => setTask(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !running && startRun(false)}
            placeholder="Describe the SQL task..."
            className="flex-1 bg-[#141414] border border-[#2a2a2a] rounded-lg px-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500/50 transition-colors"
            aria-label="Task description"
          />
          <button
            onClick={() => startRun(false)}
            disabled={running || !task.trim()}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            {running ? 'Running...' : 'Run'}
          </button>
          <button
            onClick={() => startRun(true)}
            disabled={running || !task.trim()}
            className="px-5 py-2.5 bg-[#141414] hover:bg-[#1e1e1e] border border-[#2a2a2a] disabled:opacity-40 disabled:cursor-not-allowed text-gray-300 text-sm font-medium rounded-lg transition-colors"
          >
            Dry Run
          </button>
        </div>

        {error && (
          <div className="mb-6 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
            {error}
          </div>
        )}

        <ProgressBar completed={completed} total={total} visible={progressVisible} />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {cards.map((card, i) => (
            <AgentCard key={card.sandbox_id ?? `slot-${i}`} card={card} />
          ))}
        </div>

        {competitionResult && (
          <>
            <WinnerCard result={competitionResult} visible={winnerVisible} />
            <MetricsBar result={competitionResult} visible={winnerVisible} />
          </>
        )}
      </div>
    </div>
  )
}
