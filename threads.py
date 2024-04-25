from flask import Blueprint, render_template
import requests

threads = Blueprint('threads', __name__, template_folder='template')

# TODO: move following to an app config or sqlite #########
server = 'https://social.ayco.io'
thread_ids = ['112319729193615365', '112258065967208438']
app = {
    "title":"Ayo's Threads",
    "description": "Incubator for thoughts before they become a blog."
}
attribution = {
    "owner": "Ayo Ayco",
    "year": "2024"
}
###########################################################

@threads.route('/')
def home():
    statuses = fetch_statuses()
    return render_template('threads.html', threads=statuses, app=app, attribution=attribution)

@threads.route('/<path:id>')
def thread(id):
    if id in thread_ids:
        status = fetch_thread(id)
        return render_template('threads.html', threads=[status], app=app, attribution=attribution)
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
    return clean_dict(account, ['avatar', 'display_name', 'id', 'url'])

def clean_status(status):
    clean = clean_dict(status, ['id', 'content', 'created_at', 'url', 'media_attachments', 'card'])
    clean['account'] = clean_author(status['account'])
    return clean

def clean_dict(dict, keys):
    return {k: dict[k] for k in keys}

