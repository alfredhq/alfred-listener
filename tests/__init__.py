import os
import unittest2
from flask import json
from flask_alfred_db import AlfredDB

from alfred_db.models import Repository, Commit, Base
from alfred_listener import create_app
from alfred_listener.database import db
from alfred_listener.helpers import parse_hook_data


TESTS_DIR = os.path.dirname(__file__)
FIXTURES_DIR = os.path.join(TESTS_DIR, 'fixtures')
CONFIG = os.path.join(TESTS_DIR, 'config.yml')
PAYLOAD = os.path.join(FIXTURES_DIR, 'payload.json')


class BaseTestCase(unittest2.TestCase):

    def __call__(self, result=None):
        try:
            self._pre_setup()
            with self.client:
                super(BaseTestCase, self).__call__(result)
        finally:
            self._post_teardown()

    def _pre_setup(self):
        self.app = self.create_app()
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        Base.metadata.create_all(bind=db.engine)

    def _post_teardown(self):
        db.session_class.remove()
        Base.metadata.drop_all(bind=db.engine)
        if getattr(self, '_ctx', None) is not None:
            self._ctx.pop()

    def setUp(self):
        with open(PAYLOAD) as f:
            self.payload = f.read()
        self.parsed_data = parse_hook_data(json.loads(self.payload))

    def create_app(self):
        return create_app(CONFIG)


class HookParserTestCase(BaseTestCase):

    def test_hash(self): 
        self.assertTrue('hash' in self.parsed_data.keys())
        self.assertEqual(
            self.parsed_data['hash'],
            '2e7be88382545a9dc7a05b9d2e85a7041e311075',
        )

    def test_compare_url(self):
        self.assertTrue('compare_url' in self.parsed_data.keys())
        self.assertEqual(
            self.parsed_data['compare_url'],
            'https://github.com/xobb1t/test/compare/a90ff8353403...2e7be8838254',
        )

    def test_ref(self):
        self.assertTrue('ref' in self.parsed_data.keys())
        self.assertEqual(self.parsed_data['ref'], 'refs/heads/master')

    def test_committer(self):
        self.assertTrue('committer_name' in self.parsed_data.keys())
        self.assertEqual(self.parsed_data['committer_name'], 'Dima Kukushkin')
        self.assertTrue('committer_email' in self.parsed_data.keys())
        self.assertEqual(self.parsed_data['committer_email'],
                         'dima@kukushkin.me')

    def test_repo(self):
        self.assertTrue('repo_name' in self.parsed_data.keys())
        self.assertEqual(self.parsed_data['repo_name'], 'test')
        self.assertTrue('repo_user' in self.parsed_data.keys())
        self.assertEqual(self.parsed_data['repo_user'], 'xobb1t')

    def test_message(self):
        self.assertTrue('message' in self.parsed_data.keys())
        self.assertEqual(self.parsed_data['message'], 'Update README.md')

    def test_repo_url(self):
        self.assertTrue('repo_url' in self.parsed_data.keys())
        self.assertEqual(self.parsed_data['repo_url'],
                         'https://github.com/xobb1t/test')


class WebhookHandlerTestCase(BaseTestCase):

    def test_not_allowed(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 405)
        response = self.client.post('/')
        self.assertNotEqual(response.status_code, 405)

    def test_not_acceptable(self):
        response = self.client.post('/', data={'payload': self.payload})
        self.assertEqual(response.status_code, 406)

    def test_bad_request(self):
        headers = {'X-Github-Event': 'push'}
        response = self.client.post('/', headers=headers)
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/',
                                    headers=headers,
                                    data={'payload': '{"asd": 123'})
        self.assertEqual(response.status_code, 400)

    def test_good_response_with_payload(self):
        data = {'payload': self.payload}
        headers = {'X-Github-Event': 'push'}
        response = self.client.post('/', headers=headers, data=data)
        self.assertEqual(response.status_code, 200)


class SavedDataTestCase(BaseTestCase):

    def setUp(self):
        super(SavedDataTestCase, self).setUp()
        self.repository_query = db.session.query(Repository).filter_by(
            name='test', user='xobb1t'
        )
        self.commit_query = db.session.query(Commit).filter_by(
            hash='2e7be88382545a9dc7a05b9d2e85a7041e311075'
        )

    def send_hook(self):
        data = {'payload': self.payload}
        headers = {'X-Github-Event': 'push'}
        return self.client.post('/', headers=headers, data=data)

    def test_repository_created(self):
        self.send_hook()
        self.assertIsNotNone(self.repository_query.first())

    def test_commit_created(self):
        self.send_hook()
        self.assertIsNotNone(self.commit_query.first())

    def test_repository_unique(self):
        self.send_hook()
        self.assertEqual(self.repository_query.count(), 1)
        self.send_hook()
        self.assertEqual(self.repository_query.count(), 1)

    def test_commit_unique(self):
        self.send_hook()
        self.assertEqual(self.commit_query.count(), 1)
        self.send_hook()
        self.assertEqual(self.commit_query.count(), 1)

    def test_repository_data(self):
        self.send_hook()
        repository = self.repository_query.first()
        self.assertEqual(repository.url, 'https://github.com/xobb1t/test')

    def test_commit_data(self):
        self.send_hook()
        repository = self.repository_query.first()
        commit = self.commit_query.first()
        self.assertEqual(commit.repository_id, repository.id)
        self.assertEqual(commit.message, 'Update README.md')
        self.assertEqual(commit.committer_name, 'Dima Kukushkin')
        self.assertEqual(commit.committer_email, 'dima@kukushkin.me')
        self.assertEqual(commit.ref, 'refs/heads/master')
