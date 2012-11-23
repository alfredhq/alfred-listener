import os
import unittest2

import mock
from flask import json, current_app
from flask_alfred_db import AlfredDB
from msgpack import packb

from alfred_db.models import Repository, Push, Base
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

    def test_commit_hash(self): 
        self.assertTrue('commit_hash' in self.parsed_data.keys())
        self.assertEqual(
            self.parsed_data['commit_hash'],
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

    def test_commit_message(self):
        self.assertTrue('commit_message' in self.parsed_data.keys())
        self.assertEqual(self.parsed_data['commit_message'], 'Update README.md')


class WebhookHandlerTestCase(BaseTestCase):

    def setUp(self):
        super(WebhookHandlerTestCase, self).setUp()
        self.repo_token = 'test-token'
        self.repository = Repository(
            owner_type='user', owner_name='xobb1t', github_id=3213131,
            token=self.repo_token, url='https://github.com/xobb1t/repo',
            owner_id=312313123, name='repo'
        )
        db.session.add(self.repository)
        db.session.commit()

        self.Context = mock.Mock()
        self.context = self.Context.return_value
        self.socket = self.context.socket.return_value
        self.context_patch = mock.patch('zmq.Context', self.Context)
        self.context_patch.start()

    def tearDown(self):
        super(WebhookHandlerTestCase, self).tearDown()
        db.session.delete(self.repository)
        db.session.commit()
        self.context_patch.stop()

    def test_not_allowed(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 405)
        response = self.client.post('/')
        self.assertNotEqual(response.status_code, 405)

    def test_not_acceptable(self):
        response = self.client.post('/', data={'payload': self.payload})
        self.assertEqual(response.status_code, 400)

    def test_bad_request(self):
        headers = {'X-Github-Event': 'push'}
        response = self.client.post('/', headers=headers)
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/?token={0}'.format(self.repo_token),
                                    headers=headers,
                                    data={'payload': '{"asd": 123'})
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/?token={0}'.format('blablabla'),
                                    headers=headers,
                                    data={'payload': self.payload})
        self.assertEqual(response.status_code, 404)

    def test_good_response_with_payload(self):
        data = {'payload': self.payload}
        headers = {'X-Github-Event': 'push'}
        response = self.client.post('/?token={0}'.format(self.repo_token),
                                    headers=headers, data=data)
        self.assertEqual(response.status_code, 200)

class SavedDataTestCase(BaseTestCase):

    def setUp(self):
        super(SavedDataTestCase, self).setUp()
        self.push_query = db.session.query(Push).filter_by(
            commit_hash='2e7be88382545a9dc7a05b9d2e85a7041e311075'
        )
        self.repo_token = 'test-token'
        self.repository = Repository(
            owner_type='user', owner_name='xobb1t', github_id=3213131,
            token=self.repo_token, url='https://github.com/xobb1t/repo',
            owner_id=312313123, name='repo'
        )
        db.session.add(self.repository)
        db.session.commit()

        self.Context = mock.Mock()
        self.context = self.Context.instance.return_value
        self.socket = self.context.socket.return_value
        self.context_patch = mock.patch('zmq.Context', self.Context)
        self.context_patch.start()

    def tearDown(self):
        super(SavedDataTestCase, self).tearDown()
        db.session.delete(self.repository)
        db.session.commit()
        self.context_patch.stop()

    def send_hook(self):
        data = {'payload': self.payload}
        headers = {'X-Github-Event': 'push'}
        return self.client.post('/?token={0}'.format(self.repo_token),
                                headers=headers, data=data)

    def test_push_created(self):
        self.send_hook()
        self.assertIsNotNone(self.push_query.first())

    def test_push_unique(self):
        self.send_hook()
        self.assertEqual(self.push_query.count(), 1)
        self.send_hook()
        self.assertEqual(self.push_query.count(), 1)

    def test_push_data(self):
        self.send_hook()
        push = self.push_query.first()
        self.assertEqual(push.repository_id, self.repository.id)
        self.assertEqual(push.commit_message, 'Update README.md')
        self.assertEqual(push.committer_name, 'Dima Kukushkin')
        self.assertEqual(push.committer_email, 'dima@kukushkin.me')
        self.assertEqual(push.ref, 'refs/heads/master')

    def test_report_created(self):
        self.send_hook()
        push = self.push_query.first()
        self.assertIsNotNone(push.report)

    def test_message_sent(self):
        self.send_hook()
        push = self.push_query.first()
        task = {
            'report_id': push.report.id,
            'owner_name': push.repository.owner_name,
            'repo_name': push.repository.name,
            'hash': push.commit_hash,
        }
        self.socket.send.assert_has_calls(mock.call(packb(task)))

    def test_socket_connect(self):
        self.send_hook()
        self.socket.connect.assert_has_calls(
            mock.call(current_app.config['COORDINATOR'])
        )
