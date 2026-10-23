"""Shared curation rules for the digest (PDF and web)."""

CATEGORY_ORDER = [
    "cves", "news", "ai", "war", "research",
    "blogs", "podcasts", "tools", "community", "sans", "weird",
]

CATEGORY_LABELS = {
    "cves": "Critical & CVEs",
    "news": "Cyber News",
    "ai": "AI & Security",
    "war": "Geopolitics & Cyber War",
    "research": "Research",
    "blogs": "Blogs & Commentary",
    "podcasts": "Podcasts & Learning",
    "tools": "Tools & Open Source",
    "community": "Community",
    "sans": "The SANS Corner",
    "weird": "Weird But Useful",
}

MAX_ARTICLES_PER_CATEGORY = 3
MAX_QUICK_HITS = 26


def categorize(articles):
    """Group articles into ordered category buckets plus quick hits."""
    categorized = {cat: [] for cat in CATEGORY_ORDER}
    for article in articles:
        cat = article.get("category", "news")
        if cat not in categorized:
            cat = "news"
        categorized[cat].append(article)

    quick_hits = []
    for cat in categorized:
        categorized[cat].sort(key=lambda a: a.get("published", 0), reverse=True)
        quick_hits.extend(categorized[cat][MAX_ARTICLES_PER_CATEGORY:])
        categorized[cat] = categorized[cat][:MAX_ARTICLES_PER_CATEGORY]

    quick_hits.sort(key=lambda a: a.get("published", 0), reverse=True)
    quick_hits = quick_hits[:MAX_QUICK_HITS]

    sections = [(cat, categorized[cat]) for cat in CATEGORY_ORDER if categorized[cat]]
    return sections, quick_hits


def category_counts(articles):
    counts = {}
    for article in articles:
        cat = article.get("category", "news")
        if cat not in CATEGORY_LABELS:
            cat = "news"
        counts[cat] = counts.get(cat, 0) + 1
    return [(cat, counts[cat]) for cat in CATEGORY_ORDER if cat in counts]
