from datetime import datetime, timedelta

import yaml
from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, send_file, url_for)

from .curation import CATEGORY_LABELS, categorize, category_counts
from .textutil import clean_title, initials, strip_icons

PROJECT_ROOT = None
EMAIL_RE = None

NAV_LINKS = [
    ("week", "This Week", "index"),
    ("archive", "Archive", "archive"),
    ("about", "About", "about"),
]


def _format_date(ts, fmt="%b %d, %Y"):
    try:
        return datetime.fromtimestamp(float(ts)).strftime(fmt)
    except (TypeError, ValueError, OSError):
        return ""


def _time_ago(ts):
    try:
        delta = datetime.now() - datetime.fromtimestamp(float(ts))
    except (TypeError, ValueError, OSError):
        return ""
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 3600:
        minutes = max(seconds // 60, 1)
        return f"{minutes}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    if seconds < 604800:
        return f"{seconds // 86400}d ago"
    return _format_date(ts)


def _nice_date(value, fmt="%B %d, %Y"):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").strftime(fmt)
    except (TypeError, ValueError):
        return str(value or "")



def _issue_window(issue):
    if not issue:
        return None, None
    try:
        start = datetime.strptime(issue["week_start"], "%Y-%m-%d")
        end = datetime.strptime(issue["week_end"], "%Y-%m-%d")
    except (KeyError, TypeError, ValueError):
        return None, None
    start_ts = start.timestamp()
    end_ts = (end + timedelta(days=1)).timestamp() - 1
    return start_ts, end_ts


def _issue_articles(storage, issue, fallback_days=14, limit=200):
    start_ts, end_ts = _issue_window(issue)
    articles = []
    if start_ts is not None:
        articles = storage.get_articles_between(start_ts, end_ts, limit=limit)
    if not articles:
        articles = storage.get_recent_articles(lookback_days=fallback_days, limit=limit)
    return articles


def _decorate_issues(storage, issues, max_stories=None):
    decorated = []
    for issue in issues:
        start_ts, end_ts = _issue_window(issue)
        story_count = 0
        if start_ts is not None:
            story_count = storage.get_article_count_between(start_ts, end_ts)
        if max_stories:
            story_count = min(story_count, max_stories)
        pdf_path = None
        pdf_size = ""
        if PROJECT_ROOT and issue.get("pdf_path"):
            from pathlib import Path
            candidate = Path(issue["pdf_path"])
            if not candidate.is_absolute():
                candidate = PROJECT_ROOT / candidate
            if candidate.is_file():
                pdf_path = str(candidate)
                pdf_size = f"{candidate.stat().st_size / (1024 * 1024):.1f} MB"
        issue = dict(issue)
        issue["story_count"] = story_count
        issue["year"] = (issue.get("week_end") or "")[:4]
        issue["pdf_size"] = pdf_size
        issue["has_pdf"] = pdf_path is not None
        decorated.append(issue)
    return decorated


def create_app(config_path, storage):
    global PROJECT_ROOT, EMAIL_RE
    from pathlib import Path
    import os
    import re
    import secrets

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    brand = cfg.get("branding", {})
    title = brand.get("title", "CyberSec Weekly")
    tagline = brand.get("tagline", "A weekly digest for networking professionals")
    max_total = int(cfg.get("max_articles_total", 50) or 50)

    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "templates"),
        static_folder=str(PROJECT_ROOT / "static"),
    )
    app.secret_key = (
        os.environ.get("DIGEST_SECRET")
        or cfg.get("web", {}).get("secret_key")
        or secrets.token_hex(24)
    )

    app.jinja_env.filters["datefmt"] = _format_date
    app.jinja_env.filters["nicedate"] = _nice_date
    app.jinja_env.filters["timeago"] = _time_ago
    app.jinja_env.filters["initials"] = initials
    app.jinja_env.filters["stripicons"] = strip_icons
    app.jinja_env.filters["clean_title"] = clean_title

    active_map = {
        "index": "week",
        "archive": "archive",
        "issue": "archive",
        "about": "about",
        "subscribe": "subscribe",
        "unsubscribe": "subscribe",
    }

    @app.context_processor
    def inject_globals():
        return {
            "brand": brand,
            "site_title": title,
            "tagline": tagline,
            "nav_links": NAV_LINKS,
            "active_nav": active_map.get(request.endpoint, ""),
            "year": datetime.now().year,
            "category_labels": CATEGORY_LABELS,
            "subscriber_count": storage.get_subscriber_count(),
            "source_total": len(cfg.get("feeds", [])),
        }

    def _build_stream(articles, lead_id=None):
        sections, quick_hits = categorize(articles)
        if lead_id is not None:
            sections = [(cat, [a for a in arts if a["id"] != lead_id]) for cat, arts in sections]
            sections = [(cat, arts) for cat, arts in sections if arts]
        return sections, quick_hits

    @app.route("/")
    def index():
        issue = storage.get_latest_issue()
        articles = _issue_articles(storage, issue, limit=max_total)
        sections, quick_hits = categorize(articles)

        lead = None
        if sections and sections[0][1]:
            lead = sections[0][1][0]
        sections, quick_hits = _build_stream(articles, lead["id"] if lead else None)

        counts = dict(category_counts(articles))
        source_count = len({a.get("source", "") for a in articles})

        recent_issues = _decorate_issues(storage, storage.get_archive_issues()[:3], max_total)
        issue_total = len(storage.get_archive_issues())
        if issue:
            issue_start, issue_end = issue.get("week_start", ""), issue.get("week_end", "")
        else:
            issue_start, issue_end = "", ""

        return render_template(
            "web/index.html",
            issue=issue,
            issue_start=issue_start,
            issue_end=issue_end,
            lead=lead,
            sections=sections,
            quick_hits=quick_hits,
            counts=counts,
            total_articles=len(articles),
            source_count=source_count,
            recent_issues=recent_issues,
            issue_total=issue_total,
        )

    @app.route("/archive")
    def archive():
        issues = _decorate_issues(storage, storage.get_archive_issues(), max_total)
        years = []
        for issue in issues:
            if not years or years[-1][0] != issue["year"]:
                years.append((issue["year"], []))
            years[-1][1].append(issue)

        total_stories = sum(i["story_count"] for i in issues)
        return render_template(
            "web/archive.html",
            issues=issues,
            years=years,
            issue_count=len(issues),
            total_stories=total_stories,
        )

    @app.route("/issues/<int:issue_id>")
    def issue(issue_id):
        issue_row = storage.get_issue_by_id(issue_id)
        if not issue_row:
            abort(404)
        articles = _issue_articles(storage, issue_row, limit=max_total)
        sections, quick_hits = categorize(articles)

        lead = None
        if sections and sections[0][1]:
            lead = sections[0][1][0]
        sections, quick_hits = _build_stream(articles, lead["id"] if lead else None)

        counts = dict(category_counts(articles))
        source_count = len({a.get("source", "") for a in articles})
        decorated = _decorate_issues(storage, [issue_row], max_total)[0]
        return render_template(
            "web/issue.html",
            issue=decorated,
            lead=lead,
            sections=sections,
            quick_hits=quick_hits,
            counts=counts,
            total_articles=len(articles),
            source_count=source_count,
        )

    @app.route("/about")
    def about():
        feeds = cfg.get("feeds", [])
        categories = []
        for feed in feeds:
            cat = feed.get("category", "news")
            if cat not in categories:
                categories.append(cat)
        return render_template(
            "web/about.html",
            feeds=feeds,
            feed_categories=[(c, CATEGORY_LABELS.get(c, c)) for c in categories],
        )

    @app.route("/subscribe", methods=["GET", "POST"])
    def subscribe():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            if request.form.get("website"):
                flash("Thanks — check your inbox soon.", "success")
                return redirect(url_for("subscribe"))
            if not EMAIL_RE.match(email):
                flash("That doesn't look like a valid email address. Try again.", "error")
                return redirect(url_for("subscribe"))
            result = storage.add_subscriber(email)
            if result == "exists":
                flash("You're already on the list — no action needed.", "info")
            elif result == "reactivated":
                flash("Welcome back. Your subscription has been reactivated.", "success")
            else:
                flash("You're on the list. The next issue lands in your inbox.", "success")
            return redirect(url_for("subscribe"))
        return render_template("web/subscribe.html")

    @app.post("/unsubscribe")
    def unsubscribe():
        email = (request.form.get("email") or "").strip().lower()
        if not EMAIL_RE.match(email):
            flash("Enter the email address you subscribed with.", "error")
            return redirect(url_for("subscribe"))
        if storage.deactivate_subscriber(email):
            flash("You've been removed from the mailing list.", "success")
        else:
            flash("That address wasn't found on the list.", "info")
        return redirect(url_for("subscribe"))

    @app.route("/download/<int:issue_id>")
    def download(issue_id):
        issue_row = storage.get_issue_by_id(issue_id)
        if not issue_row or not issue_row.get("pdf_path"):
            return "PDF not found", 404
        pdf_path = Path(issue_row["pdf_path"])
        if not pdf_path.is_absolute():
            pdf_path = PROJECT_ROOT / pdf_path
        if not pdf_path.is_file():
            return "PDF not found", 404
        return send_file(pdf_path, mimetype="application/pdf", as_attachment=True,
                         download_name=pdf_path.name)

    @app.route("/click/<int:article_id>")
    def track_click(article_id):
        subscriber = request.args.get("s", "")
        storage.record_click(article_id, subscriber)
        article = storage.get_article_by_id(article_id)
        if article and article.get("url"):
            return redirect(article["url"], code=302)
        return "Article not found", 404

    @app.route("/healthz")
    def healthz():
        return jsonify(status="ok", issues=len(storage.get_all_issues()))

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("web/404.html"), 404

    return app
