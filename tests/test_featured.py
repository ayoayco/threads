"""Tests for the database-backed featured posts and the OAuth gate.

Run from the project root:

    python -m unittest discover -s tests
"""
import os
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

# import `threads` as a package, not as the threads.py module in this directory
sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask

import threads as threads_package
from threads import db, featured
from threads.auth import auth
from threads.cache import cache
from threads.threads import threads as threads_blueprint

ADMIN_ID = '109334826893234870'
OTHER_ID = '999999999999999999'

def make_status(id, content='<p>hello</p>'):
    return {
        'id': id,
        'content': content,
        'created_at': '2026-01-01T00:00:00.000Z',
        'url': f'https://social.example/@owner/{id}',
        'media_attachments': [],
        'card': None,
        'tags': [],
        'emojis': [],
        'account': {
            'id': ADMIN_ID,
            'acct': 'owner',
            'display_name': 'Owner',
            'avatar': 'https://social.example/avatar.png',
            'url': 'https://social.example/@owner',
            'emojis': [],
        },
    }

def fake_get():
    """Stand in for the Mastodon API: statuses and featured tags."""
    def get(url, **kwargs):
        if '/api/v1/statuses?id[]=' in url:
            asked = parse_qs(urlparse(url).query).get('id[]', [])
            # the server answers in its own order, not the order asked for
            return Response([make_status(i) for i in sorted(asked)])
        if url.endswith('/featured_tags'):
            return Response([])
        raise AssertionError(f'unexpected request: {url}')
    return get

class Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

class ThreadsTestCase(unittest.TestCase):
    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix='.sqlite')
        os.close(handle)

        self.app = Flask('threads.app')
        self.app.config.update(
            SECRET_KEY='test-secret',
            DATABASE=self.db_path,
            TESTING=True,
            APPS={'threads': {
                'site_name': 'Thoughts',
                'title': 'Thoughts',
                'description': 'test',
                'server': 'https://social.example',
                'user_id': ADMIN_ID,
                'advisory': False,
            }},
            ATTRIBUTION={'owner': 'Owner', 'year': '2024'},
        )
        cache.init_app(self.app, config={'CACHE_TYPE': 'SimpleCache'})
        db.init_app(self.app)
        self.app.register_blueprint(threads_blueprint, url_prefix='/')
        self.app.register_blueprint(auth, url_prefix='/')
        with self.app.app_context():
            db.init_db(seed=True)
            cache.clear()
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.db_path)

    def sign_in(self, user_id=ADMIN_ID):
        with self.client.session_transaction() as session:
            session['user'] = {'id': user_id, 'acct': 'owner', 'display_name': 'Owner'}
            session['csrf_token'] = 'test-token'

### the data layer
class FeaturedStoreTest(ThreadsTestCase):
    def test_seed_reproduces_the_previously_hardcoded_order(self):
        with self.app.app_context():
            self.assertEqual(featured.list_ids()[0], '116667802375475365')
            self.assertEqual(featured.list_ids()[-1], '113449531956042438')
            self.assertEqual(len(featured.list_ids()), 13)

    def test_add_and_remove(self):
        with self.app.app_context():
            featured.add('123', host='https://social.example')
            self.assertTrue(featured.is_featured('123'))
            self.assertEqual(featured.list_ids()[0], '123')  # newest first
            featured.remove('123')
            self.assertFalse(featured.is_featured('123'))

    def test_featuring_twice_is_harmless(self):
        with self.app.app_context():
            before = len(featured.list_ids())
            featured.add('123')
            featured.add('123')
            self.assertEqual(len(featured.list_ids()), before + 1)

    def test_init_db_keeps_existing_rows(self):
        with self.app.app_context():
            featured.remove('116667802375475365')
            featured.add('123')
            db.init_db(seed=False)
            self.assertTrue(featured.is_featured('123'))
            self.assertFalse(featured.is_featured('116667802375475365'))

    def test_a_bare_filename_is_a_usable_database_path(self):
        # README offers DATABASE as an override; a relative name has no
        # directory part, and makedirs('') would raise on startup
        directory = os.path.dirname(self.db_path)
        app = Flask('threads.app')
        app.config.update(SECRET_KEY='test-secret', DATABASE='bare.sqlite')
        previous = os.getcwd()
        os.chdir(directory)
        try:
            db.init_app(app)
            with app.app_context():
                self.assertEqual(featured.list_ids(), [])
        finally:
            os.chdir(previous)
            # tolerate the file never being created, so a failure above is
            # what gets reported rather than the cleanup
            created = os.path.join(directory, 'bare.sqlite')
            if os.path.exists(created):
                os.unlink(created)

    def test_parse_status_id(self):
        cases = {
            '113449531956042438': '113449531956042438',
            '  113449531956042438 ': '113449531956042438',
            'https://social.example/@owner/113449531956042438': '113449531956042438',
            'https://social.example/@owner/113449531956042438/': '113449531956042438',
            'https://social.example/users/owner/statuses/113449531956042438':
                '113449531956042438',
            'https://social.example/@owner': None,
            'not a post': None,
            '': None,
            None: None,
        }
        for value, expected in cases.items():
            self.assertEqual(featured.parse_status_id(value), expected, value)

### mounted inside another site
class BlueprintTest(unittest.TestCase):
    """`ayco.io-flask` attaches threads under /threads, so the app's own
    directory is not this package's. Nothing here may be looked up relative to
    the application."""

    def setUp(self):
        self.elsewhere = tempfile.mkdtemp()
        self.db_path = os.path.join(self.elsewhere, 'threads.sqlite')
        self.host = Flask('host', root_path=self.elsewhere)
        self.host.config.update(
            SECRET_KEY='test-secret',
            DATABASE=self.db_path,
            TESTING=True,
            APPS={'threads': {
                'site_name': 'Thoughts',
                'title': 'Thoughts',
                'description': 'test',
                'server': 'https://social.example',
                'user_id': ADMIN_ID,
                'advisory': False,
            }},
            ATTRIBUTION={'owner': 'Owner', 'year': '2024'},
        )
        threads_package.init_app(self.host, url_prefix='/threads')

    def tearDown(self):
        for name in os.listdir(self.elsewhere):
            os.unlink(os.path.join(self.elsewhere, name))
        os.rmdir(self.elsewhere)

    def test_the_tables_are_created_from_the_packaged_schema(self):
        # schema.sql sits next to db.py, not next to the host application
        with self.host.app_context():
            self.assertEqual(featured.list_ids(), [])
            db.init_db(seed=True)
            self.assertEqual(len(featured.list_ids()), 13)

    def test_pages_render_under_the_prefix(self):
        with self.host.app_context():
            db.init_db(seed=True)
        client = self.host.test_client()
        with mock.patch('threads.threads.requests.get',
                        fake_get()):
            response = client.get('/threads/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('116667802375475365', response.get_data(as_text=True))

    def test_signing_in_is_reachable_under_the_prefix(self):
        with self.host.app_context():
            db.init_db()
            db.get_db().execute(
                'INSERT INTO oauth_clients (host, redirect_uri, client_id,'
                ' client_secret) VALUES (?, ?, ?, ?)',
                ('https://social.example', 'http://localhost/threads/oauth/callback',
                 'client-id', 'client-secret'))
            db.get_db().commit()
        response = self.host.test_client().get('/threads/login')
        self.assertEqual(response.status_code, 302)
        # the OAuth app is registered per redirect URI, and the prefix is in it
        self.assertIn('redirect_uri=http%3A%2F%2Flocalhost%2Fthreads%2Foauth%2Fcallback',
                      response.headers['Location'])

    def test_the_database_defaults_next_to_the_package(self):
        del self.host.config['DATABASE']
        app = Flask('host', root_path=self.elsewhere)
        app.config.update(self.host.config)
        default = os.path.join(os.path.dirname(os.path.abspath(db.__file__)),
                               'instance', 'threads.sqlite')
        existed = os.path.exists(default)
        try:
            db.init_app(app)
            self.assertEqual(app.config['DATABASE'], default)
        finally:
            if not existed and os.path.exists(default):
                os.unlink(default)

### the read path
class HomeTest(ThreadsTestCase):
    def test_home_lists_what_the_database_holds(self):
        with self.app.app_context():
            featured.remove('116667802375475365')
        with mock.patch('threads.threads.requests.get', fake_get()):
            body = self.client.get('/').get_data(as_text=True)
        self.assertIn('116458548126648062', body)
        self.assertNotIn('116667802375475365', body)

    def test_statuses_are_rendered_in_database_order(self):
        with mock.patch('threads.threads.requests.get', fake_get()):
            body = self.client.get('/').get_data(as_text=True)
        newest = body.index('116667802375475365')
        oldest = body.index('113449531956042438')
        self.assertLess(newest, oldest)

    def test_empty_list_does_not_call_the_api(self):
        with self.app.app_context():
            for id in featured.list_ids():
                featured.remove(id)
        def only_tags(url, **kwargs):
            self.assertTrue(url.endswith('/featured_tags'), url)
            return Response([])
        with mock.patch('threads.threads.requests.get', only_tags):
            self.assertEqual(self.client.get('/').status_code, 200)

### the OAuth gate
class CurationTest(ThreadsTestCase):
    def post(self, path, **form):
        form.setdefault('csrf_token', 'test-token')
        return self.client.post(path, data=form)

    def test_anonymous_visitors_may_not_curate(self):
        self.assertEqual(self.post('/featured', status='123').status_code, 403)
        self.assertEqual(self.post('/featured/remove', status='123').status_code, 403)
        with self.app.app_context():
            self.assertFalse(featured.is_featured('123'))

    def test_another_logged_in_account_may_not_curate(self):
        self.sign_in(user_id=OTHER_ID)
        self.assertEqual(self.post('/featured', status='123').status_code, 403)

    def test_a_forged_form_is_rejected(self):
        self.sign_in()
        response = self.client.post('/featured', data={
            'status': '123', 'csrf_token': 'wrong'})
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertFalse(featured.is_featured('123'))

    def test_the_owner_can_add_and_remove(self):
        self.sign_in()
        response = self.post(
            '/featured', status='https://social.example/@owner/123')
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertTrue(featured.is_featured('123'))

        self.assertEqual(self.post('/featured/remove', status='123').status_code, 302)
        with self.app.app_context():
            self.assertFalse(featured.is_featured('123'))

    def test_junk_input_is_reported_not_stored(self):
        self.sign_in()
        response = self.post('/featured', status='not a post')
        self.assertEqual(response.status_code, 302)
        self.assertIn('notice=', response.headers['Location'])
        with self.app.app_context():
            self.assertEqual(len(featured.list_ids()), 13)

    def test_curation_controls_are_only_for_the_owner(self):
        with mock.patch('threads.threads.requests.get', fake_get()):
            self.sign_in()
            owner_view = self.client.get('/').get_data(as_text=True)
            # the shared cache must not hand the owner's page to the public
            self.client.get('/logout')
            public_view = self.client.get('/').get_data(as_text=True)
        self.assertIn('Unfeature', owner_view)
        self.assertIn('Signed in as', owner_view)
        self.assertNotIn('Unfeature', public_view)
        self.assertNotIn('csrf_token', public_view)

    def test_a_change_is_visible_to_the_public_right_away(self):
        with mock.patch('threads.threads.requests.get', fake_get()):
            self.assertIn('116667802375475365',
                          self.client.get('/').get_data(as_text=True))
            self.sign_in()
            self.post('/featured/remove', status='116667802375475365')
            with self.client.session_transaction() as session:
                session.clear()
            self.assertNotIn('116667802375475365',
                             self.client.get('/').get_data(as_text=True))

### signing in
class LoginTest(ThreadsTestCase):
    def setUp(self):
        super().setUp()
        with self.app.app_context():
            db.get_db().execute(
                'INSERT INTO oauth_clients (host, redirect_uri, client_id, client_secret)'
                ' VALUES (?, ?, ?, ?)',
                ('https://social.example', 'http://localhost/oauth/callback',
                 'client-id', 'client-secret'))
            db.get_db().commit()

    def test_login_redirects_to_the_configured_server(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.headers['Location'].startswith(
                'https://social.example/oauth/authorize?'))
        self.assertIn('client_id=client-id', response.headers['Location'])

    def test_the_site_still_serves_without_a_secret_key(self):
        # a deployment gets the new code before SECRET_KEY reaches its
        # config.json, and only signing in may be affected by that
        self.app.config['SECRET_KEY'] = None
        client = self.app.test_client()
        with mock.patch('threads.threads.requests.get', fake_get()):
            self.assertEqual(client.get('/').status_code, 200)
        response = client.get('/login')
        self.assertEqual(response.status_code, 500)
        self.assertIn('SECRET_KEY', response.get_data(as_text=True))

    def test_callback_rejects_a_mismatched_state(self):
        self.client.get('/login')
        response = self.client.get('/oauth/callback?code=x&state=forged')
        self.assertEqual(response.status_code, 403)
        with self.client.session_transaction() as session:
            self.assertIsNone(session.get('user'))

    def test_callback_signs_in_the_owner(self):
        self.client.get('/login')
        with self.client.session_transaction() as session:
            state = session['oauth_state']
        with mock.patch('threads.auth.requests.post',
                        return_value=Response({'access_token': 'token'})), \
             mock.patch('threads.auth.requests.get',
                        return_value=Response({'id': ADMIN_ID, 'acct': 'owner',
                                               'display_name': 'Owner'})):
            response = self.client.get(f'/oauth/callback?code=x&state={state}')
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertEqual(session['user']['id'], ADMIN_ID)
        # the cookie carries an expiry, so a copy of it does not last forever
        self.assertIn('Expires=', response.headers['Set-Cookie'])

    def test_callback_refuses_any_other_account(self):
        self.client.get('/login')
        with self.client.session_transaction() as session:
            state = session['oauth_state']
        with mock.patch('threads.auth.requests.post',
                        return_value=Response({'access_token': 'token'})), \
             mock.patch('threads.auth.requests.get',
                        return_value=Response({'id': OTHER_ID, 'acct': 'someone',
                                               'display_name': 'Someone'})):
            response = self.client.get(f'/oauth/callback?code=x&state={state}')
        self.assertEqual(response.status_code, 403)
        self.assertIn('may not curate', response.get_data(as_text=True))
        with self.client.session_transaction() as session:
            self.assertIsNone(session.get('user'))

if __name__ == '__main__':
    unittest.main()
