from flask import Blueprint, render_template
import requests


threads = Blueprint('threads', __name__, template_folder='template')

server = 'https://social.ayco.io'
thread_ids = ['112319729193615365', '112258065967208438']

# TODO: fetch only parent statuses
@threads.route('/')
def home():
    statuses = fetch_statuses()
    return render_template('threads.html', threads=statuses)

# TODO: given parent status id, show page for full thread
@threads.route('/<path:id>')
def thread(id):
    thread = fetch_thread(id)
    return thread

@threads.route('/api')
def api():
    return fetch_threads();

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
    return render_template('threads.html', threads=[status])

def get_descendants(server, status):
    author_id = status['account']['id']
    context = requests.get(server + '/api/v1/statuses/' + status['id'] + '/context').json()
    descendants = []
    for reply in context['descendants']:
        if reply['account']['id'] == author_id and reply['in_reply_to_account_id'] == author_id:
            descendants.append(clean_status(reply))
    return descendants

def clean_author(account):
    return clean_dict(account, ['avatar', 'display_name', 'id'])

def clean_status(status):
    clean = clean_dict(status, ['id', 'content', 'created_at', 'url', 'media_attachments', 'card'])
    clean['account'] = clean_author(status['account'])
    return clean

def clean_dict(dict, keys):
    return {k: dict[k] for k in keys}

