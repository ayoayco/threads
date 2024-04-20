import requests
from flask import Flask

app = Flask(__name__)

server = 'https://social.ayco.io'
thread_ids = ['112294405672971916', '112258065967208438']

@app.route('/')
def home():
    threads = []
    for id in thread_ids:
        status = requests.get(server + '/api/v1/statuses/' + id ).json()
        status = clean_status(status)
        status['descendants'] = get_descendants(server, status)
        threads.append(status)
    return threads

def clean_status(status):
    return {k: status[k] for k in ['id', 'account', 'content', 'created_at', 'url', 'media_attachments', 'card']}

def get_descendants(server, status):
    author_id = status['account']['id']
    context = requests.get(server + '/api/v1/statuses/' + status['id'] + '/context').json()
    descendants = []
    for reply in context['descendants']:
        if reply['account']['id'] == author_id and reply['in_reply_to_account_id'] == author_id:
            descendants.append(clean_status(reply))
    return descendants


if __name__ == '__main__':
    app.run(host='0.0.0.0')
