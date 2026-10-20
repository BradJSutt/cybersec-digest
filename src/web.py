from pathlib import Path
from flask import Flask, send_file, render_template_string, request

import yaml

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Georgia, serif;
            background: #f5f1e8;
            color: #1a1a1a;
            padding: 40px 20px;
            line-height: 1.6;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { font-size: 2.2em; margin-bottom: 0.2em; border-bottom: 3px solid #1a1a1a; padding-bottom: 0.3em; }
        .tagline { font-style: italic; color: #555; margin-bottom: 2em; }
        .issue {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 20px 24px;
            margin-bottom: 16px;
        }
        .issue h3 { margin-bottom: 0.3em; }
        .issue .date { color: #666; font-size: 0.9em; margin-bottom: 0.8em; }
        .issue a { color: #1a1a1a; text-decoration: none; font-weight: bold; }
        .issue a:hover { text-decoration: underline; }
        .issue .dl {
            display: inline-block;
            background: #1a1a1a;
            color: #f5f1e8;
            padding: 6px 14px;
            border-radius: 3px;
            margin-top: 0.8em;
            font-size: 0.9em;
        }
        .issue .dl:hover { background: #333; text-decoration: none; }
        .empty { color: #888; font-style: italic; }
        .footer { margin-top: 3em; padding-top: 1em; border-top: 1px solid #ccc; font-size: 0.85em; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ title }}</h1>
        <p class="tagline">{{ tagline }}</p>

        {% if issues %}
            {% for issue in issues %}
            <div class="issue">
                <h3>Issue #{{ issue.id }}</h3>
                <p class="date">{{ issue.week_start }} — {{ issue.week_end }}</p>
                {% if issue.pdf_path %}
                <a class="dl" href="/download/{{ issue.id }}">Download PDF</a>
                {% endif %}
            </div>
            {% endfor %}
        {% else %}
            <p class="empty">No issues published yet. Run <code>python run.py all</code> to generate the first digest.</p>
        {% endif %}

        <div class="footer">
            <p>&copy; {{ year }} {{ title }} — Internal use only.</p>
        </div>
    </div>
</body>
</html>
"""


def create_app(config_path, storage):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    brand = cfg.get("branding", {})
    title = brand.get("title", "CyberSec Weekly")
    tagline = brand.get("tagline", "")

    app = Flask(__name__)

    @app.route("/")
    def index():
        issues = storage.get_all_issues()
        return render_template_string(
            PAGE_TEMPLATE,
            title=title,
            tagline=tagline,
            issues=issues,
            year=__import__("datetime").datetime.now().year,
        )

    @app.route("/download/<int:issue_id>")
    def download(issue_id):
        import sqlite3
        db_path = cfg.get("database", {}).get("path", "data/digest.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
        conn.close()
        if not row or not row["pdf_path"]:
            return "PDF not found", 404
        return send_file(row["pdf_path"], mimetype="application/pdf", as_attachment=True,
                         download_name=Path(row["pdf_path"]).name)

    @app.route("/click/<int:article_id>")
    def track_click(article_id):
        subscriber = request.args.get("s", "")
        storage.record_click(article_id, subscriber)
        article = storage.get_article_by_id(article_id)
        if article:
            return f'<script>window.location.href = "{article["url"]}"</script>'
        return "Article not found", 404

    return app
