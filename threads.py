from flask import Blueprint, render_template
import requests


threads = Blueprint('threads', __name__, template_folder='template')

server = 'https://social.ayco.io'
thread_ids = ['112319729193615365', '112294405672971916', '112258065967208438']

@threads.route('/')
def home():
    threads = fetch_threads();
    return render_template('index.html', threads=threads)

@threads.route('/api')
def api():
    threads = fetch_threads();
    return threads;

def fetch_threads():
    threads = []
    for id in thread_ids:
        status = requests.get(server + '/api/v1/statuses/' + id ).json()
        status = clean_status(status)
        status['descendants'] = get_descendants(server, status)
        threads.append(status)
    return threads

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

