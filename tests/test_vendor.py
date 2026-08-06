"""Tests for the browser modules served out of node_modules.

Run from the project root:

    python -m unittest discover -s tests
"""
import os
import sys
import unittest

# import `threads` as a package, not as the threads.py module in this directory
sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask

from threads.threads import threads as threads_blueprint, vendored_modules

class VendorRouteTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask('threads.app')
        # the blueprint's before_request reads the attribution year
        self.app.config.update(
            TESTING=True, ATTRIBUTION={'owner': 'Owner', 'year': '2024'})
        self.app.register_blueprint(threads_blueprint, url_prefix='/')
        self.client = self.app.test_client()

    def test_every_mapped_module_is_installed_and_served(self):
        for name in vendored_modules:
            with self.subTest(module=name):
                response = self.client.get(f'/vendor/{name}')
                self.addCleanup(response.close)
                self.assertEqual(
                    response.status_code, 200,
                    f'/vendor/{name} is not installed -- run `pnpm install`')
                self.assertIn('javascript', response.headers['Content-Type'])

    def test_the_custom_element_is_in_what_is_served(self):
        response = self.client.get('/vendor/mastodon-content.js')
        self.addCleanup(response.close)
        self.assertIn('customElements.define("mastodon-content"',
                      response.get_data(as_text=True))

    def test_the_rest_of_node_modules_is_not_reachable(self):
        # only the mapped names are served; node_modules is not a static folder
        for path in ('husky/package.json', 'web-component-base/package.json',
                     '@ayo-run/mastodon-content/dist/mastodon-content.js'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(f'/vendor/{path}').status_code, 404)

class TemplateTest(unittest.TestCase):
    templates = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'templates')

    def read(self, name):
        with open(os.path.join(self.templates, name)) as file:
            return file.read()

    def test_the_import_map_names_the_modules_the_route_serves(self):
        # a bare specifier the route doesn't serve would be a 404 in the browser
        import_map = self.read('import-map.html')
        for name in vendored_modules:
            with self.subTest(module=name):
                self.assertIn(f"filename='{name}'", import_map)

    def test_no_template_loads_a_module_from_a_cdn(self):
        # every browser module is installed from npm and served by this app
        for name in os.listdir(self.templates):
            with self.subTest(template=name):
                self.assertNotIn('esm.sh', self.read(name))
                self.assertNotIn('unpkg.com', self.read(name))

if __name__ == '__main__':
    unittest.main()
