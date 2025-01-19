from mastodon import Mastodon
from . import utils

session_id = None
account_id = None

def get_account_tagged_statuses(app, tag):
    global account_id
    mastodon = initialize_client(app)
    statuses = []
    try:
        statuses = mastodon.account_statuses(
            id=account_id,
            tagged=tag,
            exclude_reblogs=True
        )
    except:
        message = f'>>> failed to fetch statuses for ${tag}'
        raise Exception(message)

    return list(map(lambda x: utils.clean_status(x), statuses))

def initialize_client(app):
    global session_id
    global account_id
    mastodon = None
    secret = None
    try:
        secret_file = open(app['secret_file'], 'r')
        secret = secret_file.read()
    except OSError as e:
        message = '>>> No secret found.'
        print(message)

    # todo, check if access_token exist in secret_file
    if secret == None:
        #...if token does not exist, create app:
        Mastodon.create_app(
            app['site_name'],
            api_base_url = app['server'],
            to_file = app['secret_file']
        )
        try:
            mastodon = Mastodon(client_id=app['secret_file'])
            print('>>> Persisted new token!')
        except:
            message = '>>> Failed to create masto client token'
            raise Exception(message)

    else:
        #... otherwise, reuse
        try:
            mastodon = Mastodon(access_token=app['secret_file'])
            print('>>> Reused persisted token!')
        except:
            message = '>>> Persisted token did not work'
            raise Exception(message)
 
    if session_id == None:
        try:
            session_id = mastodon.log_in(
                app['user'],
                app['password'],
                to_file = app['secret_file']
            )
            print('>>> Logged in: ', session_id)
        except:
            message = '>>> Failed to get mastodon session'
            raise Exception(message)
    else:
        print('>>> Reused session: ', session_id)

    if account_id == None:
        try:
            account = mastodon.me()
            account_id = account.id
            print('>>> Set account ID: ', account_id)
        except:
            message = '>>> Failed to get mastodon account'
            raise Exception(message)
    else:
        print('>>> Reused account ID:', account_id)
 
    return mastodon