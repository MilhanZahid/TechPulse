"use client"
import Link from "next/link"
import type { Story } from "@/lib/types"
import { CATEGORY_EMOJI } from "@/lib/types"
import { formatDistanceToNow } from "date-fns"

interface Props {
  story: Story
}

function ImportanceDots({ score }: { score: number }) {
  const filled = Math.round((score / 10) * 5)
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i < filled ? "bg-blue-500" : "bg-gray-200"}`}
        />
      ))}
    </div>
  )
}

export default function NewsCard({ story }: Props) {
  const timeAgo = story.published_at
    ? formatDistanceToNow(new Date(story.published_at), { addSuffix: true })
    : formatDistanceToNow(new Date(story.created_at), { addSuffix: true })

  return (
    <Link href={`/story/${story.id}`} className="block group">
      <div className="bg-white rounded-xl border border-gray-100 p-5 hover:border-blue-200 hover:shadow-sm transition-all duration-150">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 text-sm leading-snug group-hover:text-blue-600 transition-colors line-clamp-2">
              {story.headline}
            </h3>
            {story.summary && (
              <p className="mt-1.5 text-xs text-gray-500 leading-relaxed line-clamp-2">
                {story.summary}
              </p>
            )}
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span>{timeAgo}</span>
            <span>·</span>
            <span>{story.source_count} source{story.source_count !== 1 ? "s" : ""}</span>
          </div>
          <ImportanceDots score={story.importance_score} />
        </div>
      </div>
    </Link>
  )
}
