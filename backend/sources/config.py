from dataclasses import dataclass, field
from typing import Literal

ScrapeType = Literal["web", "rss", "api"]


@dataclass
class SourceConfig:
    name: str
    url: str
    tier: int
    scrape_type: ScrapeType
    rss_url: str = ""
    selectors: dict = field(default_factory=dict)


TIER1_SOURCES: list[SourceConfig] = [
    SourceConfig(
        name="OpenAI Blog",
        url="https://openai.com/blog",
        tier=1,
        scrape_type="web",
        selectors={"article_links": "a[href*='/blog/']"},
    ),
    SourceConfig(
        name="Google DeepMind Blog",
        url="https://deepmind.google/discover/blog",
        tier=1,
        scrape_type="web",
        selectors={"article_links": "a[href*='/blog/']"},
    ),
    SourceConfig(
        name="Microsoft AI Blog",
        url="https://blogs.microsoft.com/ai",
        tier=1,
        scrape_type="rss",
        rss_url="https://blogs.microsoft.com/ai/feed/",
    ),
    SourceConfig(
        name="Meta AI Blog",
        url="https://ai.meta.com/blog",
        tier=1,
        scrape_type="web",
        selectors={"article_links": "a[href*='/blog/']"},
    ),
    SourceConfig(
        name="Apple Newsroom",
        url="https://www.apple.com/newsroom",
        tier=1,
        scrape_type="rss",
        rss_url="https://www.apple.com/newsroom/rss-feed.rss",
    ),
    SourceConfig(
        name="Nvidia Newsroom",
        url="https://nvidianews.nvidia.com",
        tier=1,
        scrape_type="rss",
        rss_url="https://nvidianews.nvidia.com/rss/",
    ),
    SourceConfig(
        name="GitHub Blog",
        url="https://github.blog",
        tier=1,
        scrape_type="rss",
        rss_url="https://github.blog/feed/",
    ),
    SourceConfig(
        name="ArXiv AI",
        url="https://arxiv.org/list/cs.AI/recent",
        tier=1,
        scrape_type="rss",
        rss_url="https://rss.arxiv.org/rss/cs.AI",
    ),
    SourceConfig(
        name="ArXiv ML",
        url="https://arxiv.org/list/cs.LG/recent",
        tier=1,
        scrape_type="rss",
        rss_url="https://rss.arxiv.org/rss/cs.LG",
    ),
    SourceConfig(
        name="Hugging Face Blog",
        url="https://huggingface.co/blog",
        tier=1,
        scrape_type="rss",
        rss_url="https://huggingface.co/blog/feed.xml",
    ),
]

TIER2_SOURCES: list[SourceConfig] = [
    SourceConfig(
        name="TechCrunch",
        url="https://techcrunch.com",
        tier=2,
        scrape_type="rss",
        rss_url="https://techcrunch.com/feed/",
    ),
    SourceConfig(
        name="The Verge",
        url="https://www.theverge.com",
        tier=2,
        scrape_type="rss",
        rss_url="https://www.theverge.com/rss/index.xml",
    ),
    SourceConfig(
        name="Wired",
        url="https://www.wired.com/tag/technology",
        tier=2,
        scrape_type="rss",
        rss_url="https://www.wired.com/feed/rss",
    ),
    SourceConfig(
        name="Ars Technica",
        url="https://arstechnica.com",
        tier=2,
        scrape_type="rss",
        rss_url="https://feeds.arstechnica.com/arstechnica/index",
    ),
    SourceConfig(
        name="MIT Technology Review",
        url="https://www.technologyreview.com",
        tier=2,
        scrape_type="rss",
        rss_url="https://www.technologyreview.com/feed/",
    ),
    SourceConfig(
        name="Reuters Technology",
        url="https://www.reuters.com/technology",
        tier=2,
        scrape_type="rss",
        rss_url="https://feeds.reuters.com/reuters/technologyNews",
    ),
]

TIER4_SOURCES: list[SourceConfig] = [
    SourceConfig(
        name="Hacker News",
        url="https://news.ycombinator.com",
        tier=4,
        scrape_type="api",
    ),
    SourceConfig(
        name="Reddit MachineLearning",
        url="https://www.reddit.com/r/MachineLearning/.json",
        tier=4,
        scrape_type="api",
    ),
    SourceConfig(
        name="Reddit Programming",
        url="https://www.reddit.com/r/programming/.json",
        tier=4,
        scrape_type="api",
    ),
    SourceConfig(
        name="Reddit Technology",
        url="https://www.reddit.com/r/technology/.json",
        tier=4,
        scrape_type="api",
    ),
    SourceConfig(
        name="Reddit Artificial",
        url="https://www.reddit.com/r/artificial/.json",
        tier=4,
        scrape_type="api",
    ),
    SourceConfig(
        name="Product Hunt",
        url="https://www.producthunt.com",
        tier=4,
        scrape_type="web",
    ),
]

ALL_SOURCES = TIER1_SOURCES + TIER2_SOURCES + TIER4_SOURCES
