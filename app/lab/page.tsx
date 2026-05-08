"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api"

interface PipelineRun {
  id: number
  started_at: string
  finished_at: string | null
  articles_scraped: number
  stories_processed: number
  status: string
  error_log: string | null
}

interface LabStatus {
  recent_runs: PipelineRun[]
  total_articles: number
  total_stories: number
}

export default function LabPage() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [ideas, setIdeas] = useState<string | null>(null)
  const [status, setStatus] = useState<LabStatus | null>(null)
  const [loadingIdeas, setLoadingIdeas] = useState(false)
  const [loadingStatus, setLoadingStatus] = useState(true)

  useEffect(() => {
    const t = localStorage.getItem("admin_token")
    if (!t) {
      router.push("/lab/login")
      return
    }
    setToken(t)
    api.getLabStatus(t)
      .then((s) => setStatus(s as LabStatus))
      .catch(() => {
        localStorage.removeItem("admin_token")
        router.push("/lab/login")
      })
      .finally(() => setLoadingStatus(false))
  }, [router])

  async function generateIdeas() {
    if (!token) return
    setLoadingIdeas(true)
    try {
      const { ideas: text } = await api.getLabIdeas(token)
      setIdeas(text)
    } catch {
      setIdeas("Failed to generate ideas. Check your API key and try again.")
    } finally {
      setLoadingIdeas(false)
    }
  }

  async function triggerScrape() {
    try {
      await api.triggerRefresh()
      if (token) {
        const s = await api.getLabStatus(token)
        setStatus(s as LabStatus)
      }
    } catch {
      alert("Scrape trigger failed")
    }
  }

  if (!token) return null

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">🔬 Lab</h1>
            <p className="text-sm text-gray-400 mt-0.5">Admin dashboard</p>
          </div>
          <a href="/" className="text-sm text-gray-400 hover:text-gray-700">← Dashboard</a>
        </div>

        {/* Project Ideas */}
        <section className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Project Ideas</h2>
            <button
              onClick={generateIdeas}
              disabled={loadingIdeas}
              className="px-4 py-2 bg-blue-500 text-white text-sm font-medium rounded-xl hover:bg-blue-600 disabled:opacity-40 transition-colors"
            >
              {loadingIdeas ? "Generating..." : "Generate Ideas"}
            </button>
          </div>
          {ideas ? (
            <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap font-mono bg-gray-50 rounded-xl p-4">
              {ideas}
            </div>
          ) : (
            <p className="text-sm text-gray-400">
              Click "Generate Ideas" to get project ideas based on today's top stories and rising trends.
            </p>
          )}
        </section>

        {/* Pipeline Status */}
        <section className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Pipeline Health</h2>
            <button
              onClick={triggerScrape}
              className="px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Trigger Scrape
            </button>
          </div>

          {loadingStatus ? (
            <div className="text-sm text-gray-400">Loading status...</div>
          ) : status ? (
            <>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <StatCard label="Total Articles" value={status.total_articles} />
                <StatCard label="Total Stories" value={status.total_stories} />
              </div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Recent Runs</h3>
              <div className="space-y-2">
                {status.recent_runs.length === 0 && (
                  <p className="text-sm text-gray-400">No pipeline runs yet.</p>
                )}
                {status.recent_runs.map((run) => (
                  <div key={run.id} className="flex items-center justify-between text-xs bg-gray-50 rounded-lg px-3 py-2">
                    <span className="text-gray-500">{new Date(run.started_at).toLocaleString()}</span>
                    <span className="text-gray-600">{run.articles_scraped} articles / {run.stories_processed} stories</span>
                    <span className={`font-medium ${run.status === "completed" ? "text-green-600" : run.status === "failed" ? "text-red-500" : "text-yellow-500"}`}>
                      {run.status}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </section>

        {/* Logout */}
        <button
          onClick={() => { localStorage.removeItem("admin_token"); router.push("/") }}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          Sign out of Lab
        </button>
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-gray-50 rounded-xl p-3">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900">{value.toLocaleString()}</p>
    </div>
  )
}
