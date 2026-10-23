"""Small display helpers shared by the web UI and the PDF renderer."""

import re

_ICON_CHARS = re.compile(r"[\ue000-\uf8ff\u200b-\u200d\ufeff\ufffd]")
_URLS = re.compile(r"https?://\S+", re.IGNORECASE)
_SPACES = re.compile(r"\s+")


def strip_icons(value):
    """Remove icon-font/private-use glyphs that render as tofu."""
    text = _ICON_CHARS.sub("", str(value or ""))
    return _SPACES.sub(" ", text).strip()


def initials(text):
    words = [w for w in strip_icons(text).replace("-", " ").split() if w]
    if not words:
        return "CS"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def clean_title(value):
    """Drop raw URLs and trailing separators that feed titles sometimes carry."""
    original = _SPACES.sub(" ", strip_icons(value)).strip()
    cleaned = _SPACES.sub(" ", _URLS.sub("", original)).strip(" -–—|·")
    return cleaned or original
