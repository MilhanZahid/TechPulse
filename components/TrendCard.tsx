import type { Trend } from "@/lib/types"
import { CATEGORY_EMOJI } from "@/lib/types"

interface Props {
  trend: Trend
  rank: number
}

export default function TrendCard({ trend, rank }: Props) {
  const emoji = CATEGORY_EMOJI[trend.topic] ?? "📈"
  const barWidth = Math.min((trend.momentum_score / 100) * 100, 100)

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-4">
      <div className="flex items-start gap-3">
        <span className="text-lg font-bold text-gray-200 w-6 shrink-0">{rank}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span>{emoji}</span>
            <span className="font-semibold text-gray-900 text-sm">{trend.topic}</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-400 mb-2">
            <span>{trend.mention_count} mentions</span>
            <span>·</span>
            <span>{trend.days_active} day{trend.days_active !== 1 ? "s" : ""} active</span>
          </div>
          <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-400 rounded-full transition-all"
              style={{ width: `${barWidth}%` }}
            />
          </div>
        </div>
        <div className="text-right shrink-0">
          <span className="text-xs font-semibold text-blue-600">
            {trend.momentum_score.toFixed(0)}
          </span>
          <p className="text-xs text-gray-400">score</p>
        </div>
      </div>
    </div>
  )
}
