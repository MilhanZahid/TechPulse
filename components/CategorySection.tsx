import type { Story } from "@/lib/types"
import { CATEGORY_EMOJI } from "@/lib/types"
import NewsCard from "./NewsCard"

interface Props {
  category: string
  stories: Story[]
}

export default function CategorySection({ category, stories }: Props) {
  const emoji = CATEGORY_EMOJI[category] ?? "📰"
  return (
    <section className="mb-8">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
        <span>{emoji}</span>
        <span>{category}</span>
        <span className="ml-auto text-xs font-normal normal-case text-gray-400">
          {stories.length} stor{stories.length !== 1 ? "ies" : "y"}
        </span>
      </h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {stories.map((s) => (
          <NewsCard key={s.id} story={s} />
        ))}
      </div>
    </section>
  )
}
