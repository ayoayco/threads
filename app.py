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
        author = status['account']['acct']
        context = requests.get(server + '/api/v1/statuses/' + id + '/context').json()
        descendants = []
        for reply in context['descendants']:
            if reply['account']['acct'] == author:
                descendants.append(clean_status(reply))
        status['descendants'] = descendants
        threads.append(clean_status(status))
    return threads

def clean_status(status):
    clean = {k: status[k] for k in {'content', 'created_at', 'url'}}
    if 'descendants' in status:
        descendants = status['descendants']
        clean['descendants_count'] = len(descendants)
        clean['descendants'] = descendants
    return clean

if __name__ == '__main__':
    app.run(host='0.0.0.0')
