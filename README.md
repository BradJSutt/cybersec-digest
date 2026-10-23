# CyberSec Weekly Digest

A locally hosted, weekly cybersecurity and technology digest that aggregates articles from 10–15 curated RSS feeds, synthesizes them into a clean 1–2 page PDF, and delivers it via email or a local web interface.

## Features

- **RSS Aggregation** — Pulls from 15 curated security/tech feeds
- **Auto-Categorization** — Sorts articles into 9 sections (Critical & CVEs, Cyber News, AI & Security, Geopolitics, Blogs, Podcasts, Tools, SANS Corner, Weird But Useful)
- **Editorial Website** — Landing page with the latest stories, archive, about and self-serve subscription pages. Articles are rendered as native HTML (not as an embedded PDF)
- **PDF Generation** — Editorial two-page layout that mirrors the site theme: masthead, lead story, card grids and quick hits, with clickable links and thumbnails
- **Email Delivery** — Weekly PDF sent to subscriber list via SMTP
- **Local Web UI** — Browse, read and download issues on your network
- **SQLite Storage** — Deduplication, click tracking, issue history, and email subscriptions

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp config.yaml.example config.yaml
# Edit config.yaml with your SMTP settings and subscriber list

# Run once (fetch + render + email)
python run.py all --send

# Or run step by step
python run.py fetch
python run.py render
python run.py email

# Start web server
python run.py serve

# Run weekly scheduler (blocking)
python run.py schedule
```

## Configuration

All settings live in `config.yaml`:

- **feeds** — Add/remove RSS sources
- **subscribers** — Email addresses for PDF delivery
- **smtp** — Mail server settings
- **schedule** — Day and time for weekly generation
- **branding** — Title, tagline, logo

## Commands

| Command | Description |
|---------|-------------|
| `python run.py fetch` | Pull latest articles from all feeds |
| `python run.py render` | Generate PDF from stored articles |
| `python run.py email` | Send latest PDF to subscribers |
| `python run.py all --send` | Fetch + render + email in one shot |
| `python run.py serve` | Start local web server |
| `python run.py schedule` | Run weekly scheduler (blocking) |

## Web Interface

`python run.py serve` starts the reader site (default `http://localhost:5000`).

| Route | Page |
|-------|------|
| `/` | This week — lead story, category sections, quick hits, PDF download |
| `/archive` | Every issue, grouped by year, with online reading and PDF download |
| `/issues/<id>` | A single issue rendered for the web |
| `/about` | How the digest works, section guide, source list, FAQ |
| `/subscribe` | Self-serve subscription and unsubscribe forms |
| `/healthz` | JSON health check for monitoring |

Subscriptions are stored in the `subscribers` table inside `data/digest.db`.
`Emailer` merges these with the `subscribers` list in `config.yaml`, so the
same addresses are used once SMTP delivery is configured.

> The web UI has no authentication. Keep it on the internal network (or change
> `output.web_host` to `127.0.0.1`) unless it sits behind an authenticated proxy.

## Project Structure

```
cybersec-digest/
├── config.yaml              # All settings
├── run.py                   # CLI entry point
├── requirements.txt         # Python dependencies
├── src/
│   ├── fetcher.py           # RSS pulling + dedup
│   ├── summarizer.py        # Article classification + summaries
│   ├── renderer.py          # HTML → PDF generation
│   ├── curation.py          # Shared category rules for PDF + web
│   ├── textutil.py          # Shared title/icon helpers for PDF + web
│   ├── emailer.py           # SMTP delivery
│   ├── web.py               # Flask reader site
│   └── storage.py           # SQLite persistence
├── templates/
│   ├── digest.html          # Jinja2 PDF template
│   └── web/                 # Site templates (base, home, archive, about...)
├── static/
│   ├── styles.css           # Digest (PDF) styling
│   ├── site.css             # Site theme
│   └── site.js              # Floating nav behaviour
├── data/
│   └── digest.db            # SQLite database
└── output/
    └── digest-YYYY-MM-DD.pdf
```

## Docker (Coming Soon)

```bash
docker build -t cybersec-digest .
docker run -v $(pwd)/config.yaml:/app/config.yaml cybersec-digest
```

## License

MIT — See LICENSE file for details.
