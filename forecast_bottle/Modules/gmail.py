"""
gmail.py

Composes and sends the feed-prediction email via Gmail SMTP.
"""

from __future__ import annotations

import smtplib
import ssl
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from .prediction import FeedPrediction


# ---------------------------------------------------------------------------
# Credentials helper (shared format with keep_data)
# ---------------------------------------------------------------------------

def _read_credentials(creds_path: str) -> dict[str, dict[str, str]]:
    creds: dict[str, dict[str, str]] = {}
    current_section: Optional[str] = None

    try:
        lines = Path(creds_path).read_text().splitlines()
    except OSError as exc:
        raise OSError(f"Unable to open credentials file: {creds_path}") from exc

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            current_section = line.lower()
            creds.setdefault(current_section, {})
        elif current_section is not None:
            key, _, value = line.partition(":")
            creds[current_section][key.strip().lower()] = value.strip()

    return creds


# ---------------------------------------------------------------------------
# Email body
# ---------------------------------------------------------------------------

def _build_body(name: str, pred: FeedPrediction, qty_label: str) -> str:
    time_next = pred.time_next.strftime("%b %d, %I:%M %p")
    time_last = pred.time_last.strftime("%b %d, %I:%M %p")
    daily_tot = int(pred.avg_daily_ml)

    # Format avg interval as "Xhr  Ymin  Zsec"
    total_secs = int(pred.avg_feed_interval.total_seconds())
    hrs, remainder = divmod(total_secs, 3600)
    mins, secs = divmod(remainder, 60)
    freq_str = f"{hrs} hrs  {mins:02d} min  {secs:02d} sec"

    lines = [
        "ESTIMATES",
        "",
        f"Next feed:  {time_next}",
        f"Amount:     {qty_label}",
        "",
        "",
        "PAST DATA",
        "",
        f"Last feed:          {time_last}",
        f"Avg daily intake:   {daily_tot} mL",
        f"Avg per feed:       {pred.avg_feed_ml} mL",
        f"Avg time between:   {freq_str}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def send_email(
    name: str,
    sender: str,
    pred: FeedPrediction,
    qty_label: str,
    creds_path: str,
    recipients_path: str,
) -> None:
    """
    Send the prediction email.

    Parameters
    ----------
    name:             Baby's name (used in the subject line).
    sender:           Display name for the From field.
    pred:             FeedPrediction dataclass from prediction.py.
    qty_label:        Formatted quantity string, e.g. "80mL (40 mins BF)".
    creds_path:       Path to credentials.txt.
    recipients_path:  Path to recipients.txt.

    Raises
    ------
    OSError       If credential or recipient files cannot be read.
    ValueError    If Gmail credentials are missing.
    smtplib.SMTPException  If the email cannot be sent.
    """
    creds = _read_credentials(creds_path)
    if "gmail" not in creds:
        raise ValueError("No 'gmail' section found in credentials file.")

    gmail_creds = creds["gmail"]
    username = gmail_creds.get("username", "")
    password = gmail_creds.get("password", "")
    if not username or not password:
        raise ValueError("Gmail username or password is missing from credentials.")

    try:
        recipients = [
            line.strip()
            for line in Path(recipients_path).read_text().splitlines()
            if line.strip()
        ]
    except OSError as exc:
        raise OSError(f"Unable to read recipients file: {recipients_path}") from exc

    if not recipients:
        raise ValueError("No recipients found in recipients file.")

    body = _build_body(name, pred, qty_label)

    msg = MIMEText(body, "plain")
    msg["Subject"] = f"{name}'s Feed Schedule"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(username, password)
        server.sendmail(username, recipients, msg.as_string())
