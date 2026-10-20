import feedparser
import time
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import yaml
import requests


class Fetcher:
    def __init__(self, config_path, storage):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.storage = storage
        self.lookback_days = self.config.get("lookback_days", 7)
        self.max_per_feed = self.config.get("max_articles_per_feed", 10)
        self.max_total = self.config.get("max_articles_total", 50)

    def fetch_all(self):
        feeds = self.config.get("feeds", [])
        total_inserted = 0

        for feed_cfg in feeds:
            try:
                count = self._fetch_feed(feed_cfg)
                total_inserted += count
            except Exception as e:
                print(f"  [WARN] Failed to fetch {feed_cfg.get('name', feed_cfg['url'])}: {e}")
                continue

        if total_inserted > self.max_total:
            total_inserted = self.max_total

        return total_inserted

    def _fetch_feed(self, feed_cfg):
        name = feed_cfg.get("name", feed_cfg["url"])
        url = feed_cfg["url"]
        feed_category = feed_cfg.get("category", "")

        resp = requests.get(url, timeout=30, headers={"User-Agent": "CyberSecWeekly/1.0"})
        resp.raise_for_status()

        parsed = feedparser.ParseResp(resp) if hasattr(feedparser, 'ParseResp') else feedparser.parse(resp.content)
        entries = parsed.entries[:self.max_per_feed]

        cutoff = time.time() - (self.lookback_days * 86400)
        inserted = 0

        for entry in entries:
            published = self._parse_date(entry)
            if published and published < cutoff:
                continue

            article_url = entry.get("link", "")
            title = entry.get("title", "").strip()
            if not article_url or not title:
                continue

            image_url = self._extract_image(entry)

            is_new = self.storage.insert_article(
                url=article_url,
                title=title,
                source=name,
                published=published or time.time(),
                image_url=image_url,
                feed_category=feed_category,
            )
            if is_new:
                inserted += 1

        print(f"  {name}: {inserted} new articles")
        return inserted

    def _parse_date(self, entry):
        for field in ["published_parsed", "updated_parsed"]:
            val = entry.get(field)
            if val:
                try:
                    return time.mktime(val)
                except (TypeError, ValueError):
                    pass

        for field in ["published", "updated"]:
            val = entry.get(field)
            if val:
                try:
                    dt = parsedate_to_datetime(val)
                    return dt.timestamp()
                except (TypeError, ValueError):
                    pass

        return None

    def _extract_image(self, entry):
        if "media_thumbnail" in entry:
            thumbs = entry.media_thumbnail
            if thumbs and len(thumbs) > 0:
                return thumbs[0].get("url", "")

        if "media_content" in entry:
            media = entry.media_content
            for m in media:
                if m.get("medium") == "image" or m.get("type", "").startswith("image/"):
                    return m.get("url", "")

        summary = entry.get("summary", "")
        if summary:
            match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
            if match:
                return match.group(1)

        return ""
