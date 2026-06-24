"""
doc_data.py

Fetches feed-log text from a Google Doc and maintains a local backup.

The backup file stores one entry per line, using the format the note uses.
Lines prefixed with "--" were present in a past backup but have since been
deleted from the Keep note itself.
"""

from __future__ import annotations

from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build


def get_content(name: str, doc_id: str, service_account_path: str, backup_path: str) -> list[str]:
    """
    Fetch the contents of a Google Doc and return as a list of strings.

    Parameters
    ----------
    name:                 Baby's name (used for the backup file header).
    doc_id:               The ID of the Google Doc (from the URL).
    service_account_path: Absolute path to the service account JSON key file.
    backup_path:          Absolute path to data_log.txt.

    Raises
    ------
    FileNotFoundError  If the service account JSON file is missing.
    Exception          If the Docs API call fails.
    """

    creds = service_account.Credentials.from_service_account_file(
        service_account_path,
        scopes=['https://www.googleapis.com/auth/documents.readonly'],
    )
    service = build('docs', 'v1', credentials=creds)
    doc = service.documents().get(documentId=doc_id).execute()

    # Extract plain text from the Doc's body content blocks.
    lines = []
    for block in doc.get('body', {}).get('content', []):
        paragraph = block.get('paragraph')
        if not paragraph:
            continue
        text = ''.join(
            el.get('textRun', {}).get('content', '')
            for el in paragraph.get('elements', [])
        )
        text = text.rstrip('\n')
        if text:
            lines.append(text)

    _update_backup(backup_path, name, lines)
    return lines


def _update_backup(backup_path: str, name: str, live_content: list[str]) -> None:
    backup = Path(backup_path)
    if not backup.exists():
        backup.write_text('')

    existing = backup.read_text().splitlines()
    header = f"{name}'s Feed History"
    existing_stripped = {
        line.lstrip('-') for line in existing if line and line != header
    }
    live_set = set(live_content)

    merged: list[str] = []
    for line in existing:
        if not line or line == header:
            continue
        bare = line.lstrip('-')
        if bare in live_set or line.startswith('--'):
            merged.append(line)
        else:
            merged.append('--' + bare)

    for item in live_content:
        if item and item not in existing_stripped:
            merged.append(item)

    backup.write_text(header + '\n\n' + '\n'.join(merged) + '\n')