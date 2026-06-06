from flask import Blueprint, render_template, current_app, redirect, url_for
import requests
from datetime import datetime
from .cache import cache
from . import utils

threads = Blueprint('threads', __name__, template_folder='templates', static_folder='static')

thread_ids = [
    '116667802375475365',
    '116458548126648062',
    '116441682011075462',
    '116381905038904377',
    '116364343818471960',
    '116352859731078602',
    '116312536977108702',
    '116245553803866191',
    '114649657564007543',
    '114490408596372783',
    '114012659479108663',
    '113650907203476875',
    '113449531956042438',
]

###########################################################

### config
def server():
    return current_app.config['APPS']['threads']['server']

def get_attribution():
    return current_app.config['ATTRIBUTION']

def get_app_config():
    return current_app.config['APPS']['threads']

def get_user_id():
    return current_app.config['APPS']['threads']['user_id']

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
    query_params = "&id[]=".join(ids)
    url = server() + '/api/v1/statuses?id[]=' + query_params
    response = requests.get(url)
    if response.status_code == 200:
        statuses = response.json()

        # When you need to check for missing statuses:
        # missing_ids = [s for s in thread_ids if not any(s in d.values() for d in statuses)]
        # print(f"missing: {missing_ids}")

        return statuses
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
@threads.route('/')
@cache.cached(timeout=300)
def home():
    app = get_app_config()
    attribution = get_attribution()
    try:
        statuses = fetch_statuses(thread_ids)
        statuses = [utils.clean_status(s) for s in statuses]
        tags = []

        # List featured hashtags
        tags = get_featured_tags()

        # Remove any `None` entries from the status list
        if statuses is None:
            statuses = []                      # fallback to an empty list
        else:
            statuses = [s for s in statuses if s]  # keep only truthy statuses

        return render_template('_home.html', threads=statuses, tags=tags, app=app, attribution=attribution, render_date=datetime.now())
    except ValueError as message:
        return render_template('_error.html', app=app, attribution=attribution, render_date=datetime.now(), message=message)



@threads.route('/tag/<path:id>')
@cache.cached(timeout=300)
def tag(id):
    attribution = get_attribution()
    app = get_app_config()
    statuses = get_account_tagged_statuses(id)

    return render_template('_tag.html', threads=statuses, tag=id, app=app, attribution=attribution, render_date=datetime.now())


@threads.route('/thread/<path:id>')
@cache.cached(timeout=300)
def thread(id):
    attribution = get_attribution()
    app = get_app_config()
    max_length = app.get('max_summary_length', 69)  # Configure max summary length
    status = fetch_thread(id)
    if status is not None:
        status['summary'] = utils.clean_html(status['content']).strip()
        if len(status['summary']) > max_length:
            status['summary'] = status['summary'][:max_length] + '...'
        return render_template('_home.html', threads=[status], app=app, attribution=attribution, render_date=datetime.now())
    else:
        return redirect(url_for('threads.home'))

@threads.route('/api')
@cache.cached(timeout=300)
def api():
    return fetch_statuses(thread_ids);

@threads.route('/api/<path:id>')
@cache.cached(timeout=300)
def api_thread(id):
    return fetch_thread(id)
