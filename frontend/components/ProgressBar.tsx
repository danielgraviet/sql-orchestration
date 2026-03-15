interface Props {
  completed: number
  total: number
  visible: boolean
}

export default function ProgressBar({ completed, total, visible }: Props) {
  if (!visible || total === 0) return null

  const pct = Math.round((completed / total) * 100)

  return (
    <div className="mb-6">
      <div className="flex justify-between text-sm text-gray-400 mb-2">
        <span>{completed}/{total} sandboxes complete</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-[#2a2a2a] rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
