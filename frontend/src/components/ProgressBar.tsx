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
      <div className="flex justify-between text-xs text-gray-500 mb-1.5">
        <span>{completed}/{total} sandboxes</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1 bg-[#2a2a2a] rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
