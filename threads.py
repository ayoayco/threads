from flask import Blueprint, render_template
import requests
from datetime import datetime, timedelta
import markdown
import re

threads = Blueprint('threads', __name__, template_folder='templates')

# TODO: move following to an app config or sqlite #########
server = 'https://social.ayco.io'
thread_ids = [
    '112461583113763423',
    '112460595916342992',
    '112457129122626146',
    '112446314845243621',
    '112438729626526601',
    '112410098697040344',
    '112400284252533385',
    '112365019457303644',
    '112360396639315016',
    '112305891918761955',
# TODO: implement pagination
#    '112258065967208438',
#    '109545132056133905'
]
app = {
    "site_name": "ayco.io/threads",
    "title":"Ayo's Threads",
    "description": "Incubator for thoughts before they become a blog."
}
attribution = {
    "owner": "Ayo Ayco",
    "year": "2022" # earliest year in featured posts
}
###########################################################

@threads.before_request
def middleware():
    # check current year and put ange as attribution
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    if year != attribution['year']:
        attribution['current_year'] = year

@threads.route('/')
def home():
    statuses = fetch_statuses()
    return render_template('threads.html', threads=statuses, app=app, attribution=attribution, render_date=datetime.now())

@threads.route('/<path:id>')
def thread(id):
    if id in thread_ids:
        status = fetch_thread(id)
        status['summary'] = clean_html(status['content']).strip()
        if len(status['summary']) > 69:
            status['summary'] = status['summary'][:69] + '...'
        return render_template('threads.html', threads=[status], app=app, attribution=attribution, render_date=datetime.now())
    else:
        return '<h1>Not Found</h1><p>¯\_(ツ)_/¯</p><a href="/">go home</a>', 404

@threads.route('/api')
def api():
    return fetch_statuses();

@threads.route('/api/<path:id>')
def api_thread(id):
    return fetch_thread(id)


def fetch_statuses():
    statuses = []
    for id in thread_ids:
        status = requests.get(server + '/api/v1/statuses/' + id ).json()
        status = clean_status(status)
        statuses.append(status)
    return statuses

def fetch_thread(id):
    status = requests.get(server + '/api/v1/statuses/' + id ).json()
    status = clean_status(status)
    status['descendants'] = get_descendants(server, status)
    return status

def get_descendants(server, status):
    author_id = status['account']['id']
    context = requests.get(server + '/api/v1/statuses/' + status['id'] + '/context').json()
    descendants = []
    for reply in context['descendants']:
        # TODO: the following condition will include a reply to a reply of the author 
        # - edge case: a different author replies in the thread and the author replies then replies again
        if reply['account']['id'] == author_id and reply['in_reply_to_account_id'] == author_id:
            descendants.append(clean_status(reply))
    return descendants

def clean_author(account):
    if 'emojis' in account and len(account['emojis']) > 0:
        name = account['display_name']
        for emoji in account['emojis']:
            account['display_name'] = name.replace(":" + emoji['shortcode'] + ":", '<img alt="' + emoji['shortcode'] + ' emoji" class="emoji" src="'+emoji['url']+'" />')

    return clean_dict(account, ['avatar', 'display_name', 'id', 'url'])

def clean_status(status):
    clean = clean_dict(status, ['id', 'content', 'created_at', 'url', 'media_attachments', 'card'])
    clean['account'] = clean_author(status['account'])
    clean['content'] = markdown.markdown("<section markdown='block'>"+ clean['content'] +"</section>", extensions=['md_in_html'])
    for emoji in status['emojis']:
        clean['content'] = clean['content'].replace(":" + emoji['shortcode'] + ":", '<img alt="' + emoji['shortcode'] + ' emoji" class="emoji" src="'+emoji['url']+'" />')
    return clean

def clean_dict(dict, keys):
    return {k: dict[k] for k in keys}

CLEANR = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')

def clean_html(raw_html):
    cleantext = re.sub(CLEANR, '', raw_html)
    return cleantext
