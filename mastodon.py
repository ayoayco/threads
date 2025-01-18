from mastodon import Mastodon
from . import utils


def get_account_tagged_statuses(app, tag):
    mastodon = initialize_client(app)
    account = mastodon.me()
    statuses = []
    try:
        statuses = mastodon.account_statuses(
            id=account.id,
            tagged=tag,
            exclude_reblogs=True
        )
    except:
        print('>>> failed to fetch statuses', tag)

    return list(map(lambda x: utils.clean_status(x), statuses))

def initialize_client(app):
    mastodon = None
    secret = None
    try:
        secret_file = open(app['secret_file'], 'r')
        secret = secret_file.read()
    except OSError as e:
        print('>>> No secret found.')

    # todo, check if access_token exist in secret_file
    if secret == None:
        #...if token does not exist, create app:
        Mastodon.create_app(
            app['site_name'],
            api_base_url = app['server'],
            to_file = app['secret_file']
        )
        mastodon = Mastodon(client_id=app['secret_file'])
        print('>>> Persisted new token!')

    else:
        #... otherwise, reuse
        mastodon = Mastodon(access_token=app['secret_file'])
        print('>>> Reused persisted token!')
 
    mastodon.log_in(
        app['user'],
        app['password'],
        to_file = app['secret_file']
    )
 
    return mastodon