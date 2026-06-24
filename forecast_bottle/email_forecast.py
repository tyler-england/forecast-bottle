"""
email_forecast.py

Entry point. Fetches feed data from Google Doc, generates a prediction,
and emails the result to all configured recipients.

Run this on a schedule (e.g. via cron) to get timely notifications.

Configuration
-------------
Set BABY_NAME and SENDER below, and ensure the following files exist in the
project root (one level above this script's parent directory):

  credentials.txt   — Google Keep & Gmail credentials
  recipients.txt    — One recipient email address per line
  age_info.txt      — Baby's birthday + age-based feed guidelines
  data_log.txt      — Empty file; used as a local feed-data backup

The Doc ID must also be set in DOC_ID below.
"""


from __future__ import annotations

import datetime
import logging
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# User configuration — edit these before running
# ---------------------------------------------------------------------------
BABY_NAME = "<baby name>"
SENDER = "<email name>"
DOC_ID = "<google doc id>"
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Resolve paths relative to the project root (two levels up from this file).
_ROOT = Path(__file__).resolve().parents[1]
CREDS_PATH = str(_ROOT / "credentials.txt")
RECIPIENTS_PATH = str(_ROOT / "recipients.txt")
AGE_DOC_PATH = str(_ROOT / "age_info.txt")
BACKUP_PATH = str(_ROOT / "data_log.txt")
LOG_PATH = str(_ROOT / "prediction_log.txt")
SERVICE_ACCOUNT_PATH = str(_ROOT / 'service_account.json')

# Keep only the N most recent log entries.
_LOG_MAX_ENTRIES = 6


def _load_prediction_log() -> list[str]:
    log = Path(LOG_PATH)
    if not log.exists():
        log.write_text("")
    return [line for line in log.read_text().splitlines() if line]


def _save_prediction_log(entries: list[str]) -> None:
    trimmed = entries[-_LOG_MAX_ENTRIES:]
    Path(LOG_PATH).write_text("\n".join(trimmed) + "\n")


def main() -> None:
    from forecast_bottle.Modules import doc_data, gmail
    from forecast_bottle.Modules.prediction import get_time_qty_summary

    # ------------------------------------------------------------------ #
    # 1. Fetch data from Google Keep                                      #
    # ------------------------------------------------------------------ #
    logger.info("Fetching data from Google Docs…")

    try:
        data = doc_data.get_content(
            name=BABY_NAME,
            doc_id=DOC_ID,
            service_account_path=SERVICE_ACCOUNT_PATH,
            backup_path=BACKUP_PATH,
        )
    except Exception as exc:
        logger.error('Failed to fetch Docs data: %s', traceback.format_exc())
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # 2. Generate prediction                                               #
    # ------------------------------------------------------------------ #
    logger.info("Generating prediction…")
    try:
        pred = get_time_qty_summary(data, age_doc_path=AGE_DOC_PATH)
    except ValueError as exc:
        logger.error("Prediction failed: %s", exc)
        sys.exit(1)

    logger.info("Predicted next feed: %s  —  %d mL", pred.time_next, pred.qty_ml)

    # ------------------------------------------------------------------ #
    # 3. Guard: skip if prediction is already in the past                 #
    # ------------------------------------------------------------------ #
    if pred.time_next <= datetime.datetime.now():
        logger.info("Predicted time is in the past — nothing to send.")
        sys.exit(0)

    # ------------------------------------------------------------------ #
    # 4. Guard: skip if this exact prediction was already sent            #
    # ------------------------------------------------------------------ #
    log_entries = _load_prediction_log()
    log_key = f"{pred.time_next} -- {pred.qty_ml} mL"

    if log_key in log_entries:
        logger.info("Prediction already sent (found in log). No email will be sent.")
        sys.exit(0)

    # ------------------------------------------------------------------ #
    # 5. Send email                                                        #
    # ------------------------------------------------------------------ #
    qty_label = f"{pred.qty_ml} mL ({pred.bf_mins} mins BF)"
    logger.info("Sending email…")
    try:
        gmail.send_email(
            name=BABY_NAME,
            sender=SENDER,
            pred=pred,
            qty_label=qty_label,
            creds_path=CREDS_PATH,
            recipients_path=RECIPIENTS_PATH,
        )
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # 6. Update log                                                        #
    # ------------------------------------------------------------------ #
    log_entries.append(log_key)
    _save_prediction_log(log_entries)
    logger.info("Email sent and log updated.")


if __name__ == "__main__":
    main()
