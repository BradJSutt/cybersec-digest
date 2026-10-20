# CyberSec Weekly Digest — Project Guide

> **Status:** v0.1 — Planning & boilerplate  
> **Owner:** Brad Sutt  
> **Team:** Networking department (5–10 professionals)  
> **License:** Intended for open-source release  
> **Repo:** https://github.com/BradJSutt (new repo TBD)

---

## 1. Project Overview

A locally hosted, weekly cybersecurity and technology digest that aggregates articles from 10–15 curated sources, synthesizes them into a clean 1–2 page read, and delivers the result as a clickable PDF via email — or through a simple web interface reachable on the local network.

---

## 2. Goals

| Goal | Details |
|------|---------|
| Aggregate | Pull latest articles from 10–15 RSS feeds |
| Synthesize | Summarize each article in 2–3 sentences with headline + link |
| Format | Output a styled PDF (newspaper-inspired, off-white background) |
| Distribute | Email the PDF to subscribers on a weekly schedule |
| Host | Run on an internal server, reachable via local DNS |
| Extend | Built as a clean boilerplate so features can be added later |
| Rank | Smart ordering — critical security news always on top, engagement-based ranking for the rest |
| Discover | Surface new podcasts, tools, and educational content automatically |
| Personalize | Learn from click patterns to elevate preferred content categories over time (v2+) |

---

## 3. Source List (RSS Feeds)

| # | Source | Feed URL | Type |
|---|--------|----------|------|
| 1 | Krebs on Security | https://krebsonsecurity.com/feed/ | News / Investigative |
| 2 | Bleeping Computer | https://www.bleepingcomputer.com/feed/ | News |
| 3 | SANS Internet Storm Center | https://isc.sans.edu/rssfeed.xml | Threat intel |
| 4 | The Hacker News | https://feeds.feedburner.com/TheHackersNews | News |
| 5 | Dark Reading | https://www.darkreading.com/rss.xml | News / Analysis |
| 6 | Schneier on Security | https://www.schneier.com/feed/atom/ | Commentary |
| 7 | CISA Advisories | https://www.cisa.gov/cybersecurity-advisories/all.xml | Alerts |
| 8 | SecurityWeek | https://www.securityweek.com/feed/ | News |
| 9 | Threatpost | https://threatpost.com/feed/ | News |
| 10 | Reddit r/netsec | https://www.reddit.com/r/netsec/.rss | Community |
| 11 | Packet Storm Security | https://packetstormsecurity.com/feeds/news/ | Exploits / Tools |
| 12 | Naked Security (Sophos) | https://nakedsecurity.sophos.com/feed/ | News / Opinion |
| 13 | Microsoft Security Blog | https://www.microsoft.com/en-us/security/blog/feed/ | Vendor / Enterprise |
| 14 | Google Project Zero | https://googleprojectzero.blogspot.com/feeds/posts/default?alt=rss | Research |
| 15 | Linux Security (LinuxSecurity.com) | https://www.linuxsecurity.com/static-content/linuxsecurity-atom.xml | News / Linux |

> Feeds can be swapped, added, or removed in the config file. All feeds are public.

---

## 4. Tech Stack

### Why Python

Python was chosen as the implementation language because it has the strongest ecosystem for exactly the problems this project solves: RSS parsing, HTML-to-PDF conversion, email delivery, and scheduling are all solved problems with mature libraries. It is also widely understood by operations teams, which matters for a tool that will live on an internal server and be maintained over time.

### Technology Choices

| Layer | Technology | Why This Choice | Alternatives Considered |
|-------|------------|-----------------|--------------------------|
| Language | Python 3.11+ | Best-in-class libraries for RSS, PDF, email. Universally known by ops teams. | Node.js (weaker PDF lib), Go (overkill for this scope) |
| RSS Parsing | `feedparser` | Industry standard. Handles malformed feeds gracefully, supports Atom + RSS, built-in date parsing. | `atoma` (less maintained), `feedparser` is the clear winner |
| HTML → PDF | `Playwright` + headless Chromium | Renders our HTML/CSS template to PDF with complete CSS support: multi-column flow, card layout, image thumbnails, clickable links, page numbers, and print styles. Runs cross-platform (Windows dev, Linux server). | WeasyPrint (native GTK/Pango dependencies — failed on Windows), fpdf2 (no CSS; manual drawing only) |
| Templating | `Jinja2` | Clean separation of content and presentation. Familiar syntax. Easy to iterate on the PDF layout without touching Python code. | Django templates (too heavy), string formatting (unmaintainable) |
| Scheduling | `APScheduler` | In-process cron-like scheduler. No external cron dependency. Supports cron expressions, interval, and date triggers. | System cron (less portable), Celery (overkill) |
| Web Interface | `Flask` (minimal) | Lightweight. Enough for a landing page with PDF download. No ORM or auth overhead needed for a local tool. | FastAPI (fine but unnecessary complexity), Django (overkill) |
| Email Delivery | `smtplib` + `MIME` | Python standard library. No external dependency. Supports TLS, authentication, attachments. | `sendgrid`/`mandrill` (external API dependency, not needed locally) |
| Database | `SQLite` | Zero-config, file-based, perfect for single-server deployment. Handles deduplication, click tracking, and issue history without a separate DB server. | PostgreSQL (overkill for 5–10 users), JSON files (query limitations) |
| Config | `YAML` | Human-readable, supports comments, widely used for application config. Easy for non-developers to edit feed lists. | JSON (no comments), TOML (less familiar to most ops teams) |
| HTTP Client | `requests` | Clean API, session support, widely understood. | `httpx` (fine but no advantage here), `urllib` (clunky) |
| HTML Parsing | `readability-lxml` | Extracts article body text for summaries. | `trafilatura` (heavier), raw regex (fragile) |
| Image / Meta Extraction | `BeautifulSoup` | Reads Open Graph, Twitter Card, and in-article image tags; also used for meta fallbacks. | regex-only parsing (brittle) |
| PDF Background | `pypdf` + `reportlab` | Prepends a paper-colored rectangle to each page's content stream so the PDF margins are cream instead of white, while leaving Chromium's text layer untouched. | PyMuPDF (AGPL license), full-page merge (duplicated text layers) |
| Packaging | `Docker` | Single-container deployment. | Bare metal (dependency management hell), virtualenv only (less portable) |

### Key Design Decisions

1. **HTML → PDF via headless Chromium, not LaTeX or direct PDF** — Writing HTML with CSS is faster to iterate, easier to style, and familiar to anyone who needs to adjust the template. Playwright renders the same HTML previewed in the browser (`output/*.html`) to PDF.
2. **SQLite, not a database server** — This is a single-server tool for 5–10 users. A file-based database removes an entire class of deployment complexity.
3. **Extractive summaries in v1, abstractive in v2** — Starting with simple extractive summaries means the pipeline works end-to-end without API keys or ML models. The summarizer module is designed to be swapped for an LLM-powered version later.
4. **APScheduler in-process, not system cron** — Keeps everything in one process, makes the Docker deployment trivial, and allows the scheduler to be paused/resumed programmatically.
5. **No authentication on the web UI** — This runs on a trusted internal network. If exposed beyond that, it should sit behind a reverse proxy with auth added.

---

## 5. Architecture (v1)

```
┌─────────────────────────────────────────────┐
│                  Scheduler                  │
│            (weekly trigger)                 │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│              Fetcher Module                 │
│  • Pull all RSS feeds                       │
│  • Filter to last 7 days                    │
│  • Deduplicate by URL                       │
│  • Store raw items in SQLite                │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│            Summarizer Module                │
│  • For each article:                        │
│    – Extract title, link, date, image       │
│    – Generate 2–3 sentence summary          │
│      (extractive first; LLM later)          │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│           PDF Renderer                      │
│  • Render HTML via Jinja2 template          │
│  • Convert to PDF via Playwright/Chromium   │
│  • Embed hero image, clickable links        │
└──────┬──────────────────────────┬───────────┘
       │                          │
       ▼                          ▼
┌──────────────┐        ┌──────────────────┐
│  Web Server  │        │  Email Sender    │
│  (Flask)     │        │  (SMTP)          │
│  LAN + DNS   │        │  Weekly PDF      │
└──────────────┘        └──────────────────┘
```

---

## 6. Content Categories

Articles are classified into these sections for the digest. Order is fixed for scanability.

### Core Sections (always present, ordered by priority)

| # | Section | Description | Examples |
|---|---------|-------------|----------|
| 1 | **Critical & CVEs** | Active exploitation, high CVSS scores, zero-days, emergency patches | CISA KEV entries, zero-day disclosures |
| 2 | **Cyber News** | Breaches, incidents, malware campaigns, threat actor activity | Ransomware attacks, APT reports |
| 3 | **Tech News** | Industry moves, product releases, M&A, regulation | Vendor acquisitions, new frameworks |
| 4 | **AI & Security** | ML/AI threats, defenses, research, policy | Prompt injection, AI-powered attacks |
| 5 | **Geopolitics & Cyber War** | Nation-state activity, cyber warfare, sanctions | APT groups, election interference |
| 6 | **Blogs & Commentary** | Expert analysis, opinions, deep dives | Krebs investigations, Schneier columns |
| 7 | **Podcasts & Learning** | New episodes, educational content, webinars | SANS podcasts, Security Now, Darknet Diaries |
| 8 | **Weird But Useful** | Unusual tools, creative exploits, offbeat research | Unusual CTF writeups, novelty projects |
| 9 | **The SANS Corner** | SANS-specific content: ISC diaries, whitepapers, podcasts | Storm Center Diary, SANS webcasts |

> Articles that fit multiple categories go into the highest-priority matching section. Classification is keyword-based in v1, ML-based in v2+.

---

## 7. Design Direction

- **Aesthetic:** Soft off-white / cream background (`#f5f1e8` or similar), reminiscent of aged newspaper paper
- **Accent colors:** Deep navy or charcoal for headlines, muted red or rust for category tags
- **Typography:** Serif for headlines (e.g., Georgia), sans-serif for body
- **Layout:** Multi-column (2-column on desktop), category sections with thin rules
- **Each article block:** Headline (clickable) → 2–3 sentence summary → source + date → thumbnail if available
- **Header:** Publication name, week range, issue number

---

## 7. Configuration

A single `config.yaml` will control:

- Feed list (add/remove sources)
- Subscriber email addresses
- SMTP server settings
- Schedule (day + time)
- Output directory
- Branding (title, logo, tagline)

---

## 8. Project Structure (Target)

```
cybersec-digest/
├── config.yaml              # Feeds, subscribers, SMTP, schedule
├── README.md                # Setup & usage
├── Dockerfile               # Container build
├── docker-compose.yml       # Optional orchestration
├── requirements.txt         # Python dependencies
├── run.py                   # Entry point — scheduler + CLI
├── src/
│   ├── fetcher.py           # RSS pulling + dedup
│   ├── summarizer.py        # Article summarization
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

---

## 9. Roadmap

### v1 — Boilerplate (Current)
- [x] Project specification document (this file)
- [ ] Project scaffolding + dependency manifest
- [ ] Fetcher: pull all 15 RSS feeds, dedup, store in SQLite
- [ ] Summarizer: extractive summaries (first 2–3 meaningful sentences)
- [x] Renderer: HTML template + Playwright/Chromium PDF output
- [ ] Emailer: SMTP delivery to subscriber list
- [ ] Scheduler: weekly cron or APScheduler trigger
- [ ] Web UI: minimal Flask page with PDF download link
- [ ] `run.py` CLI: `fetch`, `render`, `email`, `all`, `serve`

### v2 — Future Enhancements
- **Scoring & Ranking Engine** — Score articles by relevance, recency, source authority, and category weight. Critical CVEs always surface to the top regardless of score.
- **Click-Based Personalization** — Track which article types each subscriber clicks most. Over time, elevate preferred categories in their digest while maintaining critical security content at the top.
- **Podcast Discovery** — Monitor podcast RSS feeds for new episodes. Auto-generate a short paragraph summary of episode content (show notes, key topics, guest info).
- **LLM-Powered Summaries** — Abstractive summarization for richer article briefs.
- **Full-Text Extraction** — Readability-based article body extraction for better summarization input.
- **Per-User Feed Preferences** — Let subscribers opt in/out of specific categories or sources.
- **Slack/Teams Webhook Delivery** — Push digest summaries to chat channels.
- **Archive Page** — Browse past issues through the web UI.
- **Docker Image** — One-command deployment.
- **Subscription Management UI** — Self-service email subscription/unsubscription.
- **Image Proxy & Caching** — Reliable thumbnail embedding.
- **OPML Import** — Bulk feed list import.

---

## 10. Deployment Target

- Internal Linux server (Ubuntu 22.04+)
- Reachable via local DNS (e.g., `digest.internal.corp`)
- Runs as a systemd service or Docker container
- Network share or SFTP for PDF archival
- SMTP relay through company mail server

---

## 11. Open-Source Considerations

- No proprietary logic — all feeds and config are user-provided
- MIT or Apache 2.0 license
- `.env` for secrets (SMTP credentials) — never committed
- Clear README with setup instructions
- No hardcoded internal domains or IPs

---

## 12. Development Log

> **Instructions for LLMs:** Add a new entry at the bottom whenever work is done. Be concise. Include date, what was done, what's next.

| Date | Change | Next Step |
|------|--------|-----------|
| 2026-10-19 | Initial project specification created. Defined goals, tech stack, source list, architecture, and roadmap. | Begin project scaffolding — create directory structure, requirements.txt, and config.yaml. |
| 2026-10-19 | Added content categorization (9 sections incl. "Weird But Useful", "The SANS Corner"). Added future features: scoring engine, click-based personalization, podcast discovery. Updated repo reference. | Scaffold project: directory structure, requirements.txt, config.yaml, and core Python modules. |
| 2026-10-19 | Full project scaffolding complete. Created: requirements.txt, config.yaml, run.py (CLI), src/ (fetcher, summarizer, renderer, emailer, web, storage), templates/digest.html, static/styles.css, Dockerfile, .gitignore, README.md. | Test the pipeline: install deps, run `python run.py all`, verify PDF output. |
| 2026-10-19 | Pipeline tested end-to-end. Fetch: 50 articles from 13/15 feeds (2 feed errors to fix). Render: PDF generated at `output/digest-2026-10-19.pdf`. Switched from WeasyPrint to fpdf2 (native dep issues on Windows). Added text sanitizer for Unicode handling. | Fix broken feed URLs (Naked Security, Linux Security). Test email delivery with real SMTP config. |
| 2026-10-19 | Major renderer overhaul. Switched from fpdf2 to Playwright (headless Chromium) for HTML-to-PDF. Full CSS support: newspaper styling, card-based article layout, category icons, colored headings, image thumbnails, clickable links. Limited to 4 articles per category. Improved summarizer with readability-lxml extraction + key sentence scoring. | Verify PDF looks good visually. Fix broken feed URLs. Configure SMTP and test email delivery. |
| 2026-10-19 | Layout/pagination fixes. Inlined CSS into HTML (relative stylesheet was not loading under `set_content`). Fixed multi-column pagination: removed section-level break-avoid, added card-level break-avoid, `column-fill: auto`. Added cream page background underlay via pypdf + reportlab so PDF margins match the paper color. Reduced to 3 articles per category, summaries capped at 2 sentences / 320 chars, footer no longer orphaned. Working tree now 3 pages. | Fix broken feed URLs. Configure SMTP and test email delivery. |
| 2026-10-19 | Polish pass. Added Quick Hits section (remaining stories as compact links, flows inside the columns to fill the last page), stats strip in masthead (stories / quick hits / sources), Lead Story badge, and PDF footer with page numbers. Replaced pypdf merge_page underlay (duplicated text) with a prepended background rect on each page's content stream. Removed HTML colophon (now in PDF footer) so no orphan page. Synced requirements/config/docs. | Fix broken feed URLs. Configure SMTP and test email delivery. Consider LLM summaries and scoring engine next. |

---

*This document is the single source of truth for the project. Read it before making any changes. Append to the Development Log when work is completed.*
