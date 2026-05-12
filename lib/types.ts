export interface Story {
  id: number
  headline: string
  summary: string | null
  category: string | null
  importance_score: number
  source_count: number
  image_url: string | null
  published_at: string | null
  created_at: string
}

export interface Trend {
  id: number
  topic: string
  mention_count: number
  days_active: number
  momentum_score: number
  last_seen: string
}

export interface ScheduleConfig {
  refresh_times: string[]
  timezone: string
  is_active: boolean
}

export interface UserPreferences {
  interested_categories: string[]
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

export interface PipelineRun {
  id: number
  started_at: string
  finished_at: string | null
  articles_scraped: number
  stories_processed: number
  status: string
  error_log: string | null
}

export const CATEGORIES = [
  "AI & Models",
  "Chips & Hardware",
  "Dev Tools",
  "Web & Infrastructure",
  "Tech Business",
  "Security & Privacy",
  "Consumer Tech",
] as const

export const CATEGORY_EMOJI: Record<string, string> = {
  "AI & Models": "🤖",
  "Chips & Hardware": "⚡",
  "Dev Tools": "🛠️",
  "Web & Infrastructure": "🌐",
  "Tech Business": "💰",
  "Security & Privacy": "🔒",
  "Consumer Tech": "📱",
}
