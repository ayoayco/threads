import os
import sqlite3

import click
from flask import current_app, g

# schema.sql, seed.sql and instance/ belong to this package. current_app resolves
# both next to the *application*, which is the wrong directory as soon as threads
# is a blueprint of a bigger site -- see "As a blueprint" in the README.
HERE = os.path.dirname(os.path.abspath(__file__))

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def run_script(name):
    with open(os.path.join(HERE, name), encoding='utf8') as f:
        get_db().executescript(f.read())
    get_db().commit()

def init_db(seed=False):
    """Create the tables if they are missing, optionally with the starter data."""
    run_script('schema.sql')
    if seed:
        run_script('seed.sql')

@click.command('init-db')
def init_db_command():
    """Create the database and fill it with the previously hardcoded posts."""
    init_db(seed=True)
    click.echo(f"Initialized {current_app.config['DATABASE']}")

def init_app(app):
    # `instance/` inside the project, not Flask's default one level up, and
    # already in .gitignore; the same path however the app is put together.
    # Override with DATABASE in config.json to store it elsewhere.
    app.config.setdefault('DATABASE', os.path.join(HERE, 'instance', 'threads.sqlite'))
    # a bare filename has no directory part, and makedirs('') raises
    directory = os.path.dirname(app.config['DATABASE'])
    if directory:
        os.makedirs(directory, exist_ok=True)
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    # the app is useless without its tables, so never make that a manual step
    with app.app_context():
        init_db()
