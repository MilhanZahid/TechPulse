"use client"
import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import type { Story } from "@/lib/types"
import { CATEGORY_EMOJI } from "@/lib/types"
import { api } from "@/lib/api"
import ChatBox from "@/components/ChatBox"

function SkeletonBlock({ className }: { className?: string }) {
  return <div className={`bg-gray-100 rounded-lg animate-pulse ${className}`} />
}

export default function StoryPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const storyId = Number(id)

  const [story, setStory] = useState<Story | null>(null)
  const [explanation, setExplanation] = useState<string | null>(null)
  const [loadingStory, setLoadingStory] = useState(true)
  const [loadingContext, setLoadingContext] = useState(true)

  useEffect(() => {
    api.getStory(storyId)
      .then(setStory)
      .catch(() => router.push("/"))
      .finally(() => setLoadingStory(false))

    api.getStoryContext(storyId)
      .then((r) => setExplanation(r.explanation))
      .catch(() => setExplanation("Could not load explanation."))
      .finally(() => setLoadingContext(false))
  }, [storyId, router])

  if (loadingStory) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        <SkeletonBlock className="h-4 w-24" />
        <SkeletonBlock className="h-8 w-full" />
        <SkeletonBlock className="h-4 w-32" />
        <SkeletonBlock className="h-48 w-full" />
        <SkeletonBlock className="h-48 w-full" />
      </div>
    )
  }

  if (!story) return null

  const emoji = CATEGORY_EMOJI[story.category ?? ""] ?? "📰"
  const date = story.published_at
    ? new Date(story.published_at).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })
    : new Date(story.created_at).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })

  const sections = parseExplanation(explanation ?? "")

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-700 mb-6 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to dashboard
        </button>

        <div className="mb-2 flex items-center gap-2 text-xs text-gray-400">
          <span className="inline-flex items-center gap-1 bg-gray-50 border border-gray-100 rounded-full px-2 py-0.5 font-medium text-gray-500">
            {emoji} {story.category}
          </span>
          <span>·</span>
          <span>{date}</span>
          <span>·</span>
          <span>{story.source_count} source{story.source_count !== 1 ? "s" : ""}</span>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 leading-snug mb-4">
          {story.headline}
        </h1>

        {story.summary && (
          <p className="text-gray-500 text-sm leading-relaxed mb-8 border-l-2 border-blue-200 pl-4">
            {story.summary}
          </p>
        )}

        {loadingContext ? (
          <div className="space-y-6">
            {["What happened", "Background context", "What to think about it"].map((h) => (
              <div key={h}>
                <h2 className="font-semibold text-gray-900 mb-2">{h}</h2>
                <SkeletonBlock className="h-20 w-full" />
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-6 mb-8">
            {sections.map(({ heading, body }) => (
              <section key={heading}>
                <h2 className="font-semibold text-gray-900 mb-2">{heading}</h2>
                <p className="text-gray-600 text-sm leading-relaxed whitespace-pre-wrap">{body}</p>
              </section>
            ))}
            {sections.length === 0 && explanation && (
              <p className="text-gray-600 text-sm leading-relaxed whitespace-pre-wrap">{explanation}</p>
            )}
          </div>
        )}

        <hr className="border-gray-100 my-8" />

        {explanation && !loadingContext && (
          <ChatBox storyId={storyId} initialExplanation={explanation} />
        )}
      </div>
    </div>
  )
}

function parseExplanation(text: string): { heading: string; body: string }[] {
  const sections: { heading: string; body: string }[] = []
  const lines = text.split("\n")
  let currentHeading = ""
  let currentBody: string[] = []

  for (const line of lines) {
    const headingMatch = line.match(/^##\s+(.+)/)
    if (headingMatch) {
      if (currentHeading) {
        sections.push({ heading: currentHeading, body: currentBody.join("\n").trim() })
      }
      currentHeading = headingMatch[1]
      currentBody = []
    } else {
      currentBody.push(line)
    }
  }
  if (currentHeading) {
    sections.push({ heading: currentHeading, body: currentBody.join("\n").trim() })
  }
  return sections
}
