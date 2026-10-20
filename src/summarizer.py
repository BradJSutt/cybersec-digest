import re
from html import unescape

import yaml
import requests
from readability import Document
from bs4 import BeautifulSoup


BAD_IMAGE_EXTENSIONS = (".gif", ".svg", ".ico", ".webp")
BAD_IMAGE_KEYWORDS = ("logo", "icon", "avatar", "spacer", "pixel", "tracking",
                       "badge", "button", "ad-banner", "sprite", "blank",
                       "transparent", "feed", "1x1", "pixel")


CATEGORY_KEYWORDS = {
    "cves": [
        "cve-", "cvss", "zero-day", "zero day", "exploit", "ransomware",
        "critical vulnerability", "emergency patch", "actively exploited",
        "kev", "cisa advisory", "remote code execution", "rce",
    ],
    "news": [
        "breach", "leak", "hack", "attack", "malware", "phishing",
        "data breach", "cyberattack", "threat actor", "apt", "botnet",
        "credential", "stolen", "compromised",
    ],
    "ai": [
        "ai ", "artificial intelligence", "machine learning", "llm",
        "gpt", "chatbot", "deepfake", "ai-powered", "neural network",
        "prompt injection", "generative ai",
    ],
    "war": [
        "nation-state", "nation state", "cyber warfare", "cyberwar",
        "military", "war", "sanctions", "election", "espionage",
        "apt28", "apt29", "fancy bear", "cozy bear", "iran", "north korea",
        "russia", "china", "ukraine", "israel", "hamas",
    ],
    "blogs": [
        "analysis", "opinion", "commentary", "perspective", "editorial",
        "column", "interview", "q&a", "profile",
    ],
    "podcasts": [
        "podcast", "episode", "webinar", "webcast", "audio",
        "listen", "show notes",
    ],
    "weird": [
        "weird", "unusual", "strange", "bizarre", "curious",
        "ctf", "capture the flag", "wargame", "easter egg",
    ],
    "sans": [
        "sans", "isc", "storm center", "internet storm", "diary",
        "webcast", "sans whitepaper",
    ],
    "research": [
        "research", "paper", "study", "discovery", "proof of concept",
        "poc", "reverse engineering", "vulnerability research",
    ],
    "community": [
        "reddit", "community", "forum", "discussion", "ask ",
    ],
    "tools": [
        "tool", "open source", "github", "framework", "utility",
        "script", "automation",
    ],
}

CATEGORY_PRIORITY = [
    "cves", "news", "ai", "war", "research",
    "blogs", "podcasts", "tools", "community", "sans", "weird",
]


class Summarizer:
    def __init__(self, config_path, storage):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.storage = storage

    def summarize_all(self):
        articles = self.storage.get_recent_articles(
            lookback_days=self.config.get("lookback_days", 7),
            limit=self.config.get("max_articles_total", 50),
        )

        for article in articles:
            if not article.get("summary"):
                summary = self._generate_summary(article)
                category = self._classify(article["title"], article.get("source", ""))
                self.storage.update_summary(article["id"], summary, category)
                article["summary"] = summary
                article["category"] = category

        return articles

    def _generate_summary(self, article):
        url = article.get("url", "")
        title = article.get("title", "")

        if not url:
            return f"{title} — Read the full article for complete details."

        try:
            resp = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (compatible; CyberSecWeekly/1.0)"
            })
            resp.raise_for_status()
            doc = Document(resp.text)
            full_text = self._html_to_text(doc.summary())
            image_url = self._extract_image(resp.text, url)
            if image_url and not article.get("image_url"):
                self.storage.update_image(article["id"], image_url)
                article["image_url"] = image_url
            return self._extract_key_sentences(full_text, title)
        except Exception:
            return f"{title} — Read the full article for complete details."

    def _extract_image(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            img_url = og_image["content"]
            if self._is_good_image(img_url):
                return self._resolve_url(img_url, base_url)

        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            img_url = twitter_image["content"]
            if self._is_good_image(img_url):
                return self._resolve_url(img_url, base_url)

        twitter_image_src = soup.find("meta", attrs={"name": "twitter:image:src"})
        if twitter_image_src and twitter_image_src.get("content"):
            img_url = twitter_image_src["content"]
            if self._is_good_image(img_url):
                return self._resolve_url(img_url, base_url)

        article_tag = soup.find("article")
        if article_tag:
            img = article_tag.find("img")
            if img and img.get("src"):
                img_url = img["src"]
                if self._is_good_image(img_url):
                    return self._resolve_url(img_url, base_url)

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if not src:
                continue
            if self._is_good_image(src):
                return self._resolve_url(src, base_url)

        return ""

    def _is_good_image(self, url):
        if not url or url.startswith("data:"):
            return False
        url_lower = url.lower()
        if any(ext in url_lower for ext in BAD_IMAGE_EXTENSIONS):
            return False
        if any(kw in url_lower for kw in BAD_IMAGE_KEYWORDS):
            return False
        if "width=" in url_lower and any(w in url_lower for w in ["width=1", "width=2", "width=3", "width=10", "width=16", "width=32"]):
            return False
        return True

    def _resolve_url(self, url, base_url):
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http://") or url.startswith("https://"):
            return url
        from urllib.parse import urljoin
        return urljoin(base_url, url)

    def _extract_key_sentences(self, text, title, max_sentences=2):
        text = self._clean_text(text)
        if not text:
            return f"{title} — Read the full article for complete details."

        sentences = re.split(r'(?<=[.!?])\s+', text)
        title_words = set(title.lower().split())

        scored = []
        for i, sent in enumerate(sentences[:50]):
            score = 0
            words = sent.lower().split()
            overlap = sum(1 for w in words if w in title_words)
            score += overlap * 2

            if i < 5:
                score += (5 - i)

            for kw in ["announced", "revealed", "discovered", "published",
                        "reported", "confirmed", "warned", "advised"]:
                if kw in sent.lower():
                    score += 3

            if 15 < len(words) < 45:
                score += 2

            scored.append((score, sent.strip()))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:max_sentences]
        top.sort(key=lambda x: sentences.index(x[1]) if x[1] in sentences else 999)

        result = " ".join(s[1] for s in top)
        if len(result) < 80:
            return f"{title} — {result}"

        if len(result) > 320:
            result = result[:317].rsplit(" ", 1)[0] + "..."

        return result

    def _classify(self, title, source):
        text = f"{title} {source}".lower()

        for category in CATEGORY_PRIORITY:
            keywords = CATEGORY_KEYWORDS.get(category, [])
            for kw in keywords:
                if kw in text:
                    return category

        return "news"

    def _clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", text)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _html_to_text(self, html):
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
