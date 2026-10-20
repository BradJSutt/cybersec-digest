import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader


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


class Renderer:
    def __init__(self, config_path, storage):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.storage = storage
        template_dir = Path(__file__).parent.parent / "templates"
        static_dir = Path(__file__).parent.parent / "static"
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.jinja_env.filters["timestamp_date"] = self._timestamp_date
        self.static_dir = static_dir

    def _timestamp_date(self, ts):
        return datetime.fromtimestamp(ts).strftime("%b %d")

    def render(self, articles):
        now = datetime.now()
        week_start = now - timedelta(days=self.config.get("lookback_days", 7))

        brand = self.config.get("branding", {})
        title = brand.get("title", "CyberSec Weekly")
        tagline = brand.get("tagline", "")

        categorized, quick_hits = self._categorize(articles)
        total_articles = sum(len(arts) for _, arts in categorized)
        lead_id = categorized[0][1][0]["id"] if categorized and categorized[0][1] else None
        source_count = len({a.get("source", "") for a in articles})
        issue_num = self.storage.get_latest_issue()
        issue_number = (issue_num["id"] + 1) if issue_num else brand.get("issue_start", 1)

        css_content = (self.static_dir / "styles.css").read_text(encoding="utf-8")

        template = self.jinja_env.get_template("digest.html")
        html_content = template.render(
            title=title,
            tagline=tagline,
            week_start=week_start.strftime("%B %d, %Y"),
            week_end=now.strftime("%B %d, %Y"),
            issue_number=issue_number,
            generated_at=now.strftime("%B %d, %Y at %I:%M %p"),
            categorized=categorized,
            quick_hits=quick_hits,
            lead_id=lead_id,
            total_articles=total_articles,
            source_count=source_count,
            category_labels=CATEGORY_LABELS,
            css=css_content,
        )

        output_dir = Path(self.config.get("output", {}).get("directory", "output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_filename = f"digest-{now.strftime('%Y-%m-%d')}.pdf"
        pdf_path = str(output_dir / pdf_filename)

        html_path = output_dir / f"digest-{now.strftime('%Y-%m-%d')}.html"
        html_path.write_text(html_content, encoding="utf-8")

        footer_note = (
            f"{title}  \u00b7  Compiled from public RSS feeds  \u00b7  "
            f"{now.strftime('%b %d, %Y')}"
        )
        asyncio.run(self._html_to_pdf(html_content, pdf_path, footer_note))
        self._apply_page_background(pdf_path)

        self.storage.create_issue(
            week_start=week_start.strftime("%Y-%m-%d"),
            week_end=now.strftime("%Y-%m-%d"),
            pdf_path=pdf_path,
        )

        return pdf_path

    def _apply_page_background(self, pdf_path):
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import ContentStream, FloatObject

        page_bg = self.config.get("output", {}).get("page_background", "#f5f1e8")
        r, g, b = (int(page_bg.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))

        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        for page in reader.pages:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)

            cs = ContentStream(page.get_contents(), reader)
            cs.operations[0:0] = [
                ([], b"q"),
                ([FloatObject(r), FloatObject(g), FloatObject(b)], b"rg"),
                ([FloatObject(0), FloatObject(0), FloatObject(width), FloatObject(height)], b"re"),
                ([], b"f"),
                ([], b"Q"),
            ]
            page.replace_contents(cs)
            writer.add_page(page)

        with open(pdf_path, "wb") as f:
            writer.write(f)

    async def _html_to_pdf(self, html_content, pdf_path, note=""):
        from playwright.async_api import async_playwright

        footer = (
            '<div style="width:100%;padding:0 0.4in;font-family:Georgia,serif;'
            'font-size:7pt;color:#8a8a8a;display:flex;justify-content:space-between;">'
            f'<span>{note}</span>'
            '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>'
            "</div>"
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html_content, wait_until="networkidle")
            await page.emulate_media(media="print")
            await page.pdf(
                path=pdf_path,
                format="Letter",
                margin={"top": "0.5in", "bottom": "0.55in", "left": "0.4in", "right": "0.4in"},
                print_background=True,
                display_header_footer=True,
                header_template="<div></div>",
                footer_template=footer,
            )
            await browser.close()

    def _categorize(self, articles):
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

        return [(cat, categorized[cat]) for cat in CATEGORY_ORDER if categorized[cat]], quick_hits


