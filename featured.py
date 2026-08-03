import re
from urllib.parse import urlparse

from .db import get_db

# a status id as Mastodon writes them, or the tail of a status URL
STATUS_ID = re.compile(r'^[0-9]+$')

def list_ids():
    """Featured status ids, most recently featured first."""
    rows = get_db().execute(
        'SELECT status_id FROM statuses ORDER BY created DESC, id DESC'
    ).fetchall()
    return [row['status_id'] for row in rows]

def is_featured(status_id):
    row = get_db().execute(
        'SELECT 1 FROM statuses WHERE status_id = ?', (str(status_id),)
    ).fetchone()
    return row is not None

def add(status_id, host=None):
    db = get_db()
    db.execute(
        'INSERT OR IGNORE INTO statuses (status_id, host) VALUES (?, ?)',
        (str(status_id), host),
    )
    db.commit()

def remove(status_id):
    db = get_db()
    db.execute('DELETE FROM statuses WHERE status_id = ?', (str(status_id),))
    db.commit()

def parse_status_id(value):
    """Accept either a bare status id or the URL of a post; None if neither."""
    value = (value or '').strip()
    if not value:
        return None
    if STATUS_ID.match(value):
        return value
    # https://server/@user/113449531956042438 -- and /users/x/statuses/<id> forms
    path = urlparse(value).path if '/' in value else ''
    tail = path.rstrip('/').rsplit('/', 1)[-1] if path else ''
    return tail if STATUS_ID.match(tail) else None
