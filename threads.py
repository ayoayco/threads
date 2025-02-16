from flask import Blueprint, render_template, current_app
import requests
from datetime import datetime
from .cache import cache
import asyncio
import aiohttp
from . import mastodon, utils

threads = Blueprint('threads', __name__, template_folder='templates', static_folder='static')

# TODO: move following to an app config or sqlite #########
thread_ids = [
		'113986386529736815',
		'114012659479108663',
    '113775430984622212',
    '113650907203476875',
    '113449531956042438',
    '113300434695033812',
    '113210189309775644',
    '113073168505436055',
    '112979161274124372',
    '112857903897175549',
    '112857168376771706',
    '112524983806134679',
    '112461583113763423',
    '112457129122626146',
    # '112446314845243621',
    # '112438729626526601',
    # '112410098697040344',
    # '112400284252533385',
    # '112365019457303644',
    # '112360396639315016',
    # '112305891918761955',
    # '112258065967208438',
    # '111657861089216432',
    # '110639728990416918',
    # '109545132056133905'
]

###########################################################

def get_attribution():
    return current_app.config['ATTRIBUTION']

def get_app_config():
    return current_app.config['APPS']['threads']

@threads.before_request
def middleware():
    # check current year and put ange as attribution
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    attribution = get_attribution()
    if year != attribution['year']:
        attribution['current_year'] = year

@threads.route('/')
@cache.cached(timeout=300)
async def home():
    statuses = await fetch_statuses()
    attribution = get_attribution()
    app = get_app_config()
    tags = []

    masto = mastodon.initialize_client(app)

    # List featured hashtags
    tags = masto.featured_tags()

    return render_template('_home.html', threads=statuses, tags=tags, app=app, attribution=attribution, render_date=datetime.now())


@threads.route('/tag/<path:id>')
@cache.cached(timeout=300)
async def tag(id):
    attribution = get_attribution()
    app = get_app_config()
    statuses = mastodon.get_account_tagged_statuses(app, id)

    return render_template('_tag.html', threads=statuses, tag=id, app=app, attribution=attribution, render_date=datetime.now())


@threads.route('/<path:id>')
@cache.cached(timeout=300)
def thread(id):
    attribution = get_attribution()
    app = get_app_config()
    status = fetch_thread(id)
    status['summary'] = utils.clean_html(status['content']).strip()
    if len(status['summary']) > 69:
        status['summary'] = status['summary'][:69] + '...'
    return render_template('_home.html', threads=[status], app=app, attribution=attribution, render_date=datetime.now())

@threads.route('/api')
@cache.cached(timeout=300)
async def api():
    return await fetch_statuses();

@threads.route('/api/<path:id>')
@cache.cached(timeout=300)
def api_thread(id):
    return fetch_thread(id)

async def get(url, session):
    try:
        async with session.get(url, ssl=False) as response:
            res = await response.json()
            return utils.clean_status(res)
    except Exception as e:
        print(f"Unable to get url {url} due to {e.__class__}")
        return {}

def get_status_url(ser, id):
    return f'{ser}/api/v1/statuses/{id}'

def server():
    return current_app.config['APPS']['threads']['server']

async def fetch_statuses():
    statuses = []
    urls = [get_status_url(server(), id) for id in thread_ids]
    try:
        async with aiohttp.ClientSession() as session:
            statuses = await asyncio.gather(*(get(url, session) for url in urls))
            return statuses
    except:
        return None

def fetch_thread(id):
    status = requests.get(server() + '/api/v1/statuses/' + id ).json()
    status = utils.clean_status(status)
    status['descendants'] = get_descendants(server(), status)
    return status

def get_descendants(server, status):
    author_id = status['account']['id']
    context = requests.get(server + '/api/v1/statuses/' + status['id'] + '/context').json()
    descendants = []
    for reply in context['descendants']:
        # TODO: the following condition will include a reply to a reply of the author 
        # - edge case: a different author replies in the thread and the author replies then replies again
        if reply['account']['id'] == author_id and reply['in_reply_to_account_id'] == author_id:
            descendants.append(utils.clean_status(reply))
    return descendants

