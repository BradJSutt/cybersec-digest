# CyberSec Weekly Digest

A locally hosted, weekly cybersecurity and technology digest that aggregates articles from 10–15 curated RSS feeds, synthesizes them into a clean 1–2 page PDF, and delivers it via email or a local web interface.

## Features

- **RSS Aggregation** — Pulls from 15 curated security/tech feeds
- **Auto-Categorization** — Sorts articles into 9 sections (Critical & CVEs, Cyber News, AI & Security, Geopolitics, Blogs, Podcasts, Tools, SANS Corner, Weird But Useful)
- **PDF Generation** — Newspaper-style layout with off-white background, clickable links, and article thumbnails
- **Email Delivery** — Weekly PDF sent to subscriber list via SMTP
- **Local Web UI** — Browse and download past issues on your network
- **SQLite Storage** — Deduplication, click tracking, and issue history

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
│   ├── emailer.py           # SMTP delivery
│   ├── web.py               # Flask local web UI
│   └── storage.py           # SQLite persistence
├── templates/
│   └── digest.html          # Jinja2 PDF template
├── static/
│   └── styles.css           # Digest styling
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
