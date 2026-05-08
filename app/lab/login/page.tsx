"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"

export default function LabLogin() {
  const [token, setToken] = useState("")
  const [error, setError] = useState(false)
  const router = useRouter()

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!token.trim()) return
    localStorage.setItem("admin_token", token.trim())
    router.push("/lab")
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl border border-gray-100 p-8 w-full max-w-sm shadow-sm">
        <div className="text-center mb-6">
          <span className="text-3xl">🔬</span>
          <h1 className="text-xl font-bold text-gray-900 mt-2">TechPulse Lab</h1>
          <p className="text-sm text-gray-400 mt-1">Admin access required</p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-gray-500 block mb-1.5">Admin Token</label>
            <input
              type="password"
              value={token}
              onChange={(e) => { setToken(e.target.value); setError(false) }}
              placeholder="Enter your admin token"
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            {error && <p className="text-xs text-red-500 mt-1">Invalid token</p>}
          </div>
          <button
            type="submit"
            className="w-full py-2.5 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800 transition-colors"
          >
            Enter Lab
          </button>
        </form>
      </div>
    </div>
  )
}
