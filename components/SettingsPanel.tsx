"use client"
import { useEffect, useState } from "react"
import { CATEGORIES } from "@/lib/types"
import { api } from "@/lib/api"

interface Props {
  open: boolean
  onClose: () => void
}

const TIMEZONES = [
  "UTC", "America/New_York", "America/Chicago", "America/Denver",
  "America/Los_Angeles", "Europe/London", "Europe/Berlin", "Asia/Tokyo",
  "Asia/Kolkata", "Australia/Sydney",
]

export default function SettingsPanel({ open, onClose }: Props) {
  const [refreshTimes, setRefreshTimes] = useState<string[]>(["08:00", "20:00"])
  const [timezone, setTimezone] = useState("UTC")
  const [categories, setCategories] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [newTime, setNewTime] = useState("")

  useEffect(() => {
    if (!open) return
    api.getSchedule().then((s) => {
      setRefreshTimes(s.refresh_times ?? [])
      setTimezone(s.timezone ?? "UTC")
    }).catch(() => {})
    api.getPreferences().then((p) => {
      setCategories(p.interested_categories ?? [])
    }).catch(() => {})
  }, [open])

  async function save() {
    setSaving(true)
    try {
      await Promise.all([
        api.updateSchedule({ refresh_times: refreshTimes, timezone, is_active: true }),
        api.updatePreferences({ interested_categories: categories }),
      ])
      onClose()
    } finally {
      setSaving(false)
    }
  }

  function addTime() {
    if (newTime && !refreshTimes.includes(newTime)) {
      setRefreshTimes((prev) => [...prev, newTime].sort())
      setNewTime("")
    }
  }

  function toggleCategory(cat: string) {
    setCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    )
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative bg-white w-80 h-full shadow-xl flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Settings</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Schedule */}
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Refresh Schedule</h3>
            <div className="space-y-2 mb-3">
              {refreshTimes.map((t) => (
                <div key={t} className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">{t}</span>
                  <button
                    onClick={() => setRefreshTimes((prev) => prev.filter((x) => x !== t))}
                    className="text-red-400 hover:text-red-600 text-xs"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="time"
                value={newTime}
                onChange={(e) => setNewTime(e.target.value)}
                className="flex-1 text-sm border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={addTime}
                className="px-3 py-1.5 bg-blue-50 text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-100 transition-colors"
              >
                Add
              </button>
            </div>
          </section>

          {/* Timezone */}
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Timezone</h3>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
          </section>

          {/* Interests */}
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">My Interests</h3>
            <div className="space-y-2">
              {CATEGORIES.map((cat) => (
                <label key={cat} className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={categories.includes(cat)}
                    onChange={() => toggleCategory(cat)}
                    className="w-4 h-4 rounded accent-blue-500"
                  />
                  <span className="text-sm text-gray-700">{cat}</span>
                </label>
              ))}
            </div>
          </section>
        </div>

        <div className="p-5 border-t border-gray-100">
          <button
            onClick={save}
            disabled={saving}
            className="w-full py-2.5 bg-blue-500 text-white text-sm font-medium rounded-xl hover:bg-blue-600 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </div>
    </div>
  )
}
