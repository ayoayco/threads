import functools
import hmac
import secrets
from urllib.parse import urlencode

import requests
from flask import Blueprint, abort, current_app, redirect, request, session, url_for

from . import utils
from .config import get_app_config, get_user_id, server
from .db import get_db

auth = Blueprint('auth', __name__, template_folder='templates')

# enough to read who is logged in -- nothing is ever posted on their behalf
SCOPES = 'read:accounts'

# someone is waiting on a page while these run, so never hang on them
TIMEOUT = 10

### session
def enabled():
    """OAuth needs a signed session cookie, so a SECRET_KEY is required."""
    return bool(current_app.secret_key)

def current_user():
    return session.get('user')

def is_admin():
    """Only the account the site is built from may curate it."""
    user = current_user()
    return bool(user) and str(user.get('id')) == get_user_id()

@auth.app_context_processor
def inject_user():
    return {'user': current_user()}

def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not is_admin():
            abort(403, description='Only the account this site is built from can '
                                   'curate it. Sign in at /login.')
        return view(*args, **kwargs)
    return wrapped

### CSRF
def csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']

def check_csrf():
    sent = request.form.get('csrf_token', '')
    known = session.get('csrf_token', '')
    if not known or not hmac.compare_digest(sent, known):
        abort(400, description='Invalid CSRF token')

### OAuth client
def redirect_uri():
    return url_for('auth.callback', _external=True)

def get_client():
    """The registered OAuth app for this server, registering it on first use."""
    host = server()
    uri = redirect_uri()
    db = get_db()
    row = db.execute(
        'SELECT client_id, client_secret FROM oauth_clients'
        ' WHERE host = ? AND redirect_uri = ?',
        (host, uri),
    ).fetchone()
    if row is not None:
        return row['client_id'], row['client_secret']

    url = f'{host}/api/v1/apps'
    response = requests.post(url, data={
        'client_name': get_app_config().get('site_name', 'threads'),
        'redirect_uris': uri,
        'scopes': SCOPES,
        'website': uri,
    }, timeout=TIMEOUT)
    if response.status_code != 200:
        message = f'app registration returned: {response.status_code} for {url}'
        current_app.logger.error(message)
        raise ValueError(message)

    client = response.json()
    db.execute(
        'INSERT INTO oauth_clients (host, redirect_uri, client_id, client_secret)'
        ' VALUES (?, ?, ?, ?)',
        (host, uri, client['client_id'], client['client_secret']),
    )
    db.commit()
    return client['client_id'], client['client_secret']

def exchange_code(code):
    client_id, client_secret = get_client()
    url = f'{server()}/oauth/token'
    response = requests.post(url, data={
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri(),
        'scope': SCOPES,
    }, timeout=TIMEOUT)
    if response.status_code != 200:
        message = f'token exchange returned: {response.status_code} for {url}'
        current_app.logger.error(message)
        raise ValueError(message)
    return response.json()['access_token']

def verify_credentials(token):
    url = f'{server()}/api/v1/accounts/verify_credentials'
    response = requests.get(url, headers={'Authorization': f'Bearer {token}'},
                            timeout=TIMEOUT)
    if response.status_code != 200:
        message = f'verify_credentials returned: {response.status_code} for {url}'
        current_app.logger.error(message)
        raise ValueError(message)
    return response.json()

def revoke(token):
    try:
        client_id, client_secret = get_client()
        requests.post(f'{server()}/oauth/revoke', data={
            'client_id': client_id,
            'client_secret': client_secret,
            'token': token,
        }, timeout=TIMEOUT)
    except (ValueError, requests.RequestException) as error:
        # logging out locally matters more than the server-side revocation
        current_app.logger.error(f'could not revoke token: {error}')

### routes
@auth.route('/login')
def login():
    try:
        if not enabled():
            raise ValueError('SECRET_KEY is not set in config.json')
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        query = urlencode({
            'client_id': get_client()[0],
            'redirect_uri': redirect_uri(),
            'response_type': 'code',
            'scope': SCOPES,
            'state': state,
        })
        return redirect(f'{server()}/oauth/authorize?{query}')
    except requests.RequestException as message:
        return utils.render_error(message), 502
    except ValueError as message:
        return utils.render_error(message), 500

@auth.route('/oauth/callback')
def callback():
    try:
        if not enabled():
            raise ValueError('SECRET_KEY is not set in config.json')

        state = session.pop('oauth_state', None)
        if not state or not hmac.compare_digest(request.args.get('state', ''), state):
            raise ValueError('the login attempt could not be verified, please retry')
        if 'code' not in request.args:
            raise ValueError(request.args.get('error_description', 'login was denied'))

        token = exchange_code(request.args['code'])
        account = verify_credentials(token)
        if str(account['id']) != get_user_id():
            revoke(token)
            raise ValueError(f"@{account['acct']} may not curate this site")

        # signing out clears the cookie and revokes the token, but the cookie
        # itself is only trusted for as long as PERMANENT_SESSION_LIFETIME
        session.permanent = True
        session['user'] = {
            'id': str(account['id']),
            'acct': account['acct'],
            'display_name': account.get('display_name') or account['acct'],
        }
        session['token'] = token
        return redirect(url_for('threads.home'))
    except requests.RequestException as message:
        return utils.render_error(message), 502
    except ValueError as message:
        return utils.render_error(message), 403

@auth.route('/logout')
def logout():
    token = session.pop('token', None)
    if token:
        revoke(token)
    session.clear()
    return redirect(url_for('threads.home'))
