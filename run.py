#!/usr/bin/env python3
"""CyberSec Weekly Digest — entry point."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.fetcher import Fetcher
from src.summarizer import Summarizer
from src.renderer import Renderer
from src.emailer import Emailer
from src.storage import Storage
from src.web import create_app


def cmd_fetch(args):
    storage = Storage(args.config)
    fetcher = Fetcher(args.config, storage)
    count = fetcher.fetch_all()
    print(f"Fetched {count} new articles.")


def cmd_render(args):
    storage = Storage(args.config)
    summarizer = Summarizer(args.config, storage)
    renderer = Renderer(args.config, storage)
    articles = summarizer.summarize_all()
    pdf_path = renderer.render(articles)
    print(f"PDF generated: {pdf_path}")


def cmd_email(args):
    storage = Storage(args.config)
    emailer = Emailer(args.config, storage)
    emailer.send_latest()
    print("Email sent to all subscribers.")


def cmd_all(args):
    storage = Storage(args.config)
    fetcher = Fetcher(args.config, storage)
    summarizer = Summarizer(args.config, storage)
    renderer = Renderer(args.config, storage)
    emailer = Emailer(args.config, storage)

    count = fetcher.fetch_all()
    print(f"Fetched {count} new articles.")

    articles = summarizer.summarize_all()
    pdf_path = renderer.render(articles)
    print(f"PDF generated: {pdf_path}")

    if args.send:
        emailer.send_latest()
        print("Email sent to all subscribers.")


def cmd_serve(args):
    storage = Storage(args.config)
    app = create_app(args.config, storage)
    from yaml import safe_load
    with open(args.config) as f:
        cfg = safe_load(f)
    host = cfg.get("output", {}).get("web_host", "0.0.0.0")
    port = cfg.get("output", {}).get("web_port", 5000)
    app.run(host=host, port=port, debug=args.debug)


def cmd_schedule(args):
    from apscheduler.schedulers.blocking import BlockingScheduler
    from yaml import safe_load
    import datetime

    with open(args.config) as f:
        cfg = safe_load(f)

    sched_cfg = cfg.get("schedule", {})
    day = sched_cfg.get("day", "monday")
    hour = sched_cfg.get("hour", 6)
    minute = sched_cfg.get("minute", 0)

    day_map = {
        "monday": "mon", "tuesday": "tue", "wednesday": "wed",
        "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun"
    }
    day_of_week = day_map.get(day.lower(), "mon")

    scheduler = BlockingScheduler()
    scheduler.add_job(
        lambda: cmd_all(argparse.Namespace(config=args.config, send=True)),
        "cron", day_of_week=day_of_week, hour=hour, minute=minute
    )
    print(f"Scheduled weekly digest for {day}s at {hour:02d}:{minute:02d}")
    print("Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nScheduler stopped.")


def main():
    parser = argparse.ArgumentParser(description="CyberSec Weekly Digest")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("fetch", help="Fetch all RSS feeds")
    subparsers.add_parser("render", help="Render PDF from stored articles")
    subparsers.add_parser("email", help="Email latest PDF to subscribers")

    all_parser = subparsers.add_parser("all", help="Fetch, render, and optionally email")
    all_parser.add_argument("--send", action="store_true", help="Send email after rendering")

    serve_parser = subparsers.add_parser("serve", help="Run local web server")
    serve_parser.add_argument("--debug", action="store_true")

    subparsers.add_parser("schedule", help="Run weekly scheduler")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "fetch": cmd_fetch,
        "render": cmd_render,
        "email": cmd_email,
        "all": cmd_all,
        "serve": cmd_serve,
        "schedule": cmd_schedule,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
