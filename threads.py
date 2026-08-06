from flask import Blueprint, abort, render_template, current_app, redirect, request, send_from_directory, url_for
import requests
import os
from datetime import datetime
from .cache import cache
from . import featured, utils
from .auth import admin_required, check_csrf, csrf_token, is_admin
from .config import get_app_config, get_attribution, get_user_id, server

threads = Blueprint('threads', __name__, template_folder='templates', static_folder='static')

###########################################################

### featured tags
def get_account_tagged_statuses(tag_name):
    id = get_user_id()
    ser = server()
    url = f'{ser}/api/v1/accounts/{id}/statuses?exclude_replies=true&tagged={tag_name}'
    response = requests.get(url)
    if response.status_code == 200:
        statuses = response.json()
        statuses = [utils.clean_status(s) for s in statuses]
        return statuses
    else:
        message=f"get_account_tagged_statuses returned: {response.status_code} for {url}"
        current_app.logger.error(message)
        raise ValueError(message)

def get_featured_tags():
    id = get_user_id()
    ser = server()
    url = f'{ser}/api/v1/accounts/{id}/featured_tags'
    response = requests.get(url)
    if response.status_code == 200:
        tags = response.json()
        return tags
    else:
        message=f"get_featured_tags returned: {response.status_code} for {url}"
        current_app.logger.error(message)
        raise ValueError(message)

### middleware
@threads.before_request
def middleware():
    # check current year and put ange as attribution
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    attribution = get_attribution()
    if year != attribution['year']:
        attribution['current_year'] = year

### statuses
def get_status_url(ser, id):
    return f'{ser}/api/v1/statuses/{id}'

def fetch_statuses(ids):
    if not ids:
        return []
    query_params = "&id[]=".join(ids)
    url = server() + '/api/v1/statuses?id[]=' + query_params
    response = requests.get(url)
    if response.status_code == 200:
        statuses = response.json()

        # the API makes no promise about ordering, and a status deleted since it
        # was featured simply comes back missing
        found = {str(s['id']): s for s in statuses}
        return [found[id] for id in ids if id in found]
    else:
        message=f"fetch_statuses returned: {response.status_code} for {url}"
        current_app.logger.error(message)
        raise ValueError(message)

def fetch_thread(id):
    url = server() + '/api/v1/statuses/' + id
    response = requests.get(url)
    if response.status_code == 200:
        status = response.json()
        status = utils.clean_status(status)
        status['descendants'] = get_descendants(server(), status)
        return status
    else:
        message=f"fetch_thread returned: {response.status_code} for {url}"
        current_app.logger.error(message)
        raise ValueError(message)

def get_descendants(server, status):
    author_id = status['account']['id']
    url = server + '/api/v1/statuses/' + status['id'] + '/context'
    response = requests.get(url)
    if response.status_code == 200:
        context = response.json()
        descendants = []
        for reply in context['descendants']:
            # TODO: the following condition will include a reply to a reply of the author
            # - edge case: a different author replies in the thread and the author replies then replies again
            if reply['account']['id'] == author_id and reply['in_reply_to_account_id'] == author_id:
                descendants.append(utils.clean_status(reply))
        return descendants
    else:
        message=f"get_descendants returned: {response.status_code} for {url}"
        current_app.logger.error(message)
        raise ValueError(message)

### routes
# the cache is shared by every visitor, so a signed-in curator never reads from
# it -- otherwise the management controls would be served to the public
@threads.route('/')
@cache.cached(timeout=300, unless=is_admin)
def home():
    app = get_app_config()
    attribution = get_attribution()
    admin = is_admin()
    try:
        statuses = fetch_statuses(featured.list_ids())
        statuses = [utils.clean_status(s) for s in statuses]
        tags = []

        # List featured hashtags
        tags = get_featured_tags()

        # Remove any `None` entries from the status list
        if statuses is None:
            statuses = []                      # fallback to an empty list
        else:
            statuses = [s for s in statuses if s]  # keep only truthy statuses

        return render_template('_home.html', threads=statuses, tags=tags, app=app,
                               attribution=attribution, render_date=datetime.now(),
                               manage=admin, csrf_token=csrf_token() if admin else None,
                               notice=request.args.get('notice') if admin else None)
    except ValueError as message:
        return render_template('_error.html', app=app, attribution=attribution, render_date=datetime.now(), message=message)



@threads.route('/tag/<path:id>')
@cache.cached(timeout=300, unless=is_admin)
def tag(id):
    attribution = get_attribution()
    app = get_app_config()
    try:
        statuses = get_account_tagged_statuses(id)

        return render_template('_tag.html', threads=statuses, tag=id, app=app, attribution=attribution, render_date=datetime.now())
    except ValueError as message:
        return render_template('_error.html', app=app, attribution=attribution, render_date=datetime.now(), message=message)



@threads.route('/thread/<path:id>')
@cache.cached(timeout=300, unless=is_admin)
def thread(id):
    attribution = get_attribution()
    app = get_app_config()
    try:
        max_length = app.get('max_summary_length', 69)  # Configure max summary length
        status = fetch_thread(id)
        if status is not None:
            status['summary'] = utils.clean_html(status['content']).strip()
            if len(status['summary']) > max_length:
                status['summary'] = status['summary'][:max_length] + '...'
            return render_template('_home.html', threads=[status], app=app, attribution=attribution, render_date=datetime.now())
        else:
            return redirect(url_for('threads.home'))
    except ValueError as message:
        return render_template('_error.html', app=app, attribution=attribution, render_date=datetime.now(), message=message)


@threads.route('/api')
@cache.cached(timeout=300)
def api():
    return fetch_statuses(featured.list_ids());

@threads.route('/api/<path:id>')
@cache.cached(timeout=300)
def api_thread(id):
    return fetch_thread(id)

### browser modules installed from npm
# there is no bundler in this project, so the browser is served the installed
# files as they are; templates/import-map.html maps each bare specifier here.
# Only the modules listed below are reachable -- not the rest of node_modules.
node_modules = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node_modules')

vendored_modules = {
    'mastodon-content.js': '@ayo-run/mastodon-content/dist/mastodon-content.js',
    'web-component-base.js': 'web-component-base/dist/index.js',
    # the bundled build: index.js pulls in siblings by relative path, which
    # would need a route per file; bundle.js is the same code in one file
    'relative-time-element.js': '@github/relative-time-element/dist/bundle.js',
}

@threads.route('/vendor/<path:filename>')
def vendor(filename):
    path = vendored_modules.get(filename)
    if path is None:
        abort(404)
    return send_from_directory(node_modules, path)

### curating the featured list, as the account the site is built from
@threads.route('/featured', methods=['POST'])
@admin_required
def feature():
    check_csrf()
    status_id = featured.parse_status_id(request.form.get('status'))
    if status_id is None:
        return redirect(url_for('threads.home', notice='Not a status id or post URL'))
    featured.add(status_id, host=server())
    cache.clear()
    return redirect(url_for('threads.home', notice=f'Featured {status_id}'))

@threads.route('/featured/remove', methods=['POST'])
@admin_required
def unfeature():
    check_csrf()
    status_id = featured.parse_status_id(request.form.get('status'))
    if status_id is None:
        return redirect(url_for('threads.home', notice='Not a status id or post URL'))
    featured.remove(status_id)
    cache.clear()
    return redirect(url_for('threads.home', notice=f'Removed {status_id}'))

@threads.app_errorhandler(400)
@threads.app_errorhandler(403)
def handle_refusal(error):
    return utils.render_error(error.description), error.code
