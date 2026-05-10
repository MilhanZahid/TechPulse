"use client"
import { useState, useEffect, useCallback } from "react"
import type { Story, Trend } from "@/lib/types"
import { api } from "@/lib/api"
import TabNav from "@/components/TabNav"
import CategorySection from "@/components/CategorySection"
import TrendCard from "@/components/TrendCard"
import NewsCard from "@/components/NewsCard"
import SettingsPanel from "@/components/SettingsPanel"

const TABS = [
  { id: "brief", label: "Today's Brief" },
  { id: "trends", label: "Rising Trends" },
  { id: "interests", label: "My Interests" },
]

export default function Dashboard() {
  const [tab, setTab] = useState("brief")
  const [brief, setBrief] = useState<Record<string, Story[]>>({})
  const [trends, setTrends] = useState<Trend[]>([])
  const [interests, setInterests] = useState<Story[]>([])
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [b, t, i] = await Promise.all([
        api.getBrief(),
        api.getTrends(),
        api.getInterests(),
      ])
      setBrief(b)
      setTrends(t)
      setInterests(i)
      setLastUpdated(new Date())
    } catch (err) {
      console.error("Failed to load data", err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleRefresh() {
    setRefreshing(true)
    try {
      await api.triggerRefresh()
      await loadData()
    } finally {
      setRefreshing(false)
    }
  }

  const totalStories = Object.values(brief).flat().length

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-gray-100 sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl font-bold text-gray-900">TechPulse</span>
            {lastUpdated && (
              <span className="text-xs text-gray-400 hidden sm:block">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors disabled:opacity-40"
            >
              <svg className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
            <button
              onClick={() => setSettingsOpen(true)}
              className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
              title="Settings"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>
        </div>
        <div className="max-w-5xl mx-auto px-4">
          <TabNav tabs={TABS} active={tab} onChange={setTab} />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
            Loading stories...
          </div>
        ) : (
          <>
            {tab === "brief" && (
              totalStories === 0 ? (
                <EmptyState onRefresh={handleRefresh} refreshing={refreshing} />
              ) : (
                Object.entries(brief).map(([cat, stories]) => (
                  <CategorySection key={cat} category={cat} stories={stories} />
                ))
              )
            )}

            {tab === "trends" && (
              trends.length === 0 ? (
                <EmptyState onRefresh={handleRefresh} refreshing={refreshing} message="No trends yet. Run a refresh to start tracking." />
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {trends.map((t, i) => (
                    <TrendCard key={t.id} trend={t} rank={i + 1} />
                  ))}
                </div>
              )
            )}

            {tab === "interests" && (
              <>
                <div className="flex justify-end mb-4">
                  <button
                    onClick={() => setSettingsOpen(true)}
                    className="text-xs text-blue-500 hover:text-blue-600"
                  >
                    Edit preferences →
                  </button>
                </div>
                {interests.length === 0 ? (
                  <EmptyState
                    onRefresh={() => setSettingsOpen(true)}
                    refreshing={false}
                    message="No stories for your interests yet. Set your preferences in Settings."
                    cta="Open Settings"
                  />
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {interests.map((s) => (
                      <NewsCard key={s.id} story={s} />
                    ))}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>

      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}

function EmptyState({
  onRefresh,
  refreshing,
  message = "No stories yet for today. Click refresh to fetch the latest tech news.",
  cta = "Refresh Now",
}: {
  onRefresh: () => void
  refreshing: boolean
  message?: string
  cta?: string
}) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <p className="text-gray-400 text-sm mb-4 max-w-xs">{message}</p>
      <button
        onClick={onRefresh}
        disabled={refreshing}
        className="px-4 py-2 bg-blue-500 text-white text-sm font-medium rounded-xl hover:bg-blue-600 disabled:opacity-40 transition-colors"
      >
        {refreshing ? "Refreshing..." : cta}
      </button>
    </div>
  )
}
