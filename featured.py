import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import click
from flask.cli import with_appcontext

from .db import get_db

# a status id as Mastodon writes them, or the tail of a status URL
STATUS_ID = re.compile(r'^[0-9]+$')

def list_ids():
    """Featured status ids, newest post first.

    The order is the posts' own, not the order they were featured in, so a post
    from long ago takes its place down the page rather than the top. Nothing is
    stored for that: a Mastodon status id is a snowflake whose high bits are the
    time it was posted, so sorting by the id sorts by date -- numerically, since
    the id is kept as text and "123" would otherwise come after "116...".
    """
    rows = get_db().execute(
        'SELECT status_id FROM statuses ORDER BY CAST(status_id AS INTEGER) DESC'
    ).fetchall()
    return [row['status_id'] for row in rows]

def posted_at(status_id):
    """When a status was posted, read out of its snowflake id (UTC)."""
    # Mastodon: 48 bits of milliseconds since the epoch, then 16 bits of sequence
    return datetime.fromtimestamp((int(status_id) >> 16) / 1000, tz=timezone.utc)

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

@click.command('list-featured')
@with_appcontext
def list_featured_command():
    """Print the featured posts in the order the site lists them."""
    for status_id in list_ids():
        click.echo(f"{posted_at(status_id):%Y-%m-%d %H:%M}  {status_id}")

def init_app(app):
    app.cli.add_command(list_featured_command)

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
