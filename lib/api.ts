import type { Story, Trend, ScheduleConfig, UserPreferences } from "./types"

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  getBrief: () => request<Record<string, Story[]>>("/brief"),
  getTrends: () => request<Trend[]>("/trends"),
  getInterests: () => request<Story[]>("/interests"),
  getStory: (id: number) => request<Story>(`/story/${id}`),
  getStoryContext: (id: number) =>
    request<{ explanation: string }>(`/story/${id}/context`, { method: "POST" }),
  sendChat: (id: number, message: string) =>
    request<{ reply: string }>(`/story/${id}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  getSchedule: () => request<ScheduleConfig>("/schedule"),
  updateSchedule: (data: ScheduleConfig) =>
    request("/schedule", { method: "POST", body: JSON.stringify(data) }),
  getPreferences: () => request<UserPreferences>("/preferences"),
  updatePreferences: (data: UserPreferences) =>
    request("/preferences", { method: "POST", body: JSON.stringify(data) }),
  triggerRefresh: () => request("/refresh", { method: "POST" }),
  getLabIdeas: (token: string) =>
    request<{ ideas: string }>("/lab/ideas", {
      method: "POST",
      headers: { "admin-token": token },
    }),
  getLabStatus: (token: string) =>
    request("/lab/status", { headers: { "admin-token": token } }),
}
