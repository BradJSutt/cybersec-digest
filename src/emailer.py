import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

import yaml


class Emailer:
    def __init__(self, config_path, storage):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.storage = storage

    def send_latest(self):
        issue = self.storage.get_latest_issue()
        if not issue or not issue.get("pdf_path"):
            print("No PDF available to send.")
            return

        pdf_path = issue["pdf_path"]
        if not Path(pdf_path).exists():
            print(f"PDF not found: {pdf_path}")
            return

        subscribers = self.config.get("subscribers", [])
        if not subscribers:
            print("No subscribers configured.")
            return

        smtp_cfg = self.config.get("smtp", {})
        host = smtp_cfg.get("host", "localhost")
        port = smtp_cfg.get("port", 25)
        username = smtp_cfg.get("username", "")
        password = smtp_cfg.get("password", "")
        use_tls = smtp_cfg.get("use_tls", False)
        from_addr = smtp_cfg.get("from_address", "digest@localhost")
        from_name = smtp_cfg.get("from_name", "CyberSec Weekly")

        brand = self.config.get("branding", {})
        title = brand.get("title", "CyberSec Weekly")

        for subscriber in subscribers:
            msg = MIMEMultipart()
            msg["From"] = f"{from_name} <{from_addr}>"
            msg["To"] = subscriber
            msg["Subject"] = f"{title} — {issue['week_end']}"

            body = f"""
            <html>
            <body style="font-family: Georgia, serif; color: #1a1a1a; background: #f5f1e8; padding: 20px;">
                <h2>{title}</h2>
                <p>Week of {issue['week_start']} — {issue['week_end']}</p>
                <p>Your weekly cybersecurity digest is attached as a PDF.</p>
                <hr style="border: 1px solid #ccc;">
                <p style="font-size: 12px; color: #666;">
                    You are receiving this because you subscribed to {title}.<br>
                    To unsubscribe, contact your system administrator.
                </p>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, "html"))

            with open(pdf_path, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                pdf_attachment.add_header(
                    "Content-Disposition", "attachment",
                    filename=Path(pdf_path).name
                )
                msg.attach(pdf_attachment)

            with smtplib.SMTP(host, port) as server:
                if use_tls:
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)

            print(f"  Sent to {subscriber}")
