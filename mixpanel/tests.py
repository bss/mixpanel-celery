from __future__ import absolute_import

import base64
import json
import unittest
import urllib
import urllib2
import urlparse

from celery.exceptions import RetryTaskError

from mock import MagicMock as Mock
import mock

from . import tasks
from .conf import settings as mp_settings


class TestCase(unittest.TestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        patcher = mock.patch('urllib2.urlopen')
        self.addCleanup(patcher.stop)
        self.mock_urlopen = patcher.start()
        self.mock_urlopen.return_value.read.return_value = '1'

        # Setup token for mixpanel
        mp_settings.MIXPANEL_API_TOKEN = 'testmixpanel'

    @staticmethod
    def assertDictEqual(a, b):
        assert a == b, "Dicts are not equal.\nExpected: %s\nActual: %s" % (
            json.dumps(b, indent=3, sort_keys=True),
            json.dumps(a, indent=3, sort_keys=True))

    def _test_any(self, task, *args, **kwargs):
        result = kwargs.pop('result', True)
        server = kwargs.pop('server', mp_settings.MIXPANEL_API_SERVER)
        endpoint = kwargs.pop('endpoint', mp_settings.MIXPANEL_TRACKING_ENDPOINT)
        data = kwargs.pop('data', {})

        actual = task(*args, **kwargs)

        self.assertTrue(self.mock_urlopen.called)
        self.assertEqual(actual, result)

        url = self.mock_urlopen.call_args[0][0]
        scheme, netloc, path, params, querystr, frag = urlparse.urlparse(url)
        query = urlparse.parse_qs(querystr, keep_blank_values=True, strict_parsing=True)
        self.assertEqual(netloc, server)
        self.assertEqual(path, endpoint)
        self.assertEqual(query.keys(), ['data'])
        datastr = base64.b64decode(query['data'][0])
        actual = json.loads(datastr)
        self.assertDictEqual(actual, data)


class EventTrackerTest(TestCase):
    def _test_event(self, *args, **kwargs):
        return self._test_any(tasks.event_tracker, *args, **kwargs)

    def test_event(self):
        self._test_event('clicked button',
            data={
                "event": "clicked button",
                "properties": { "token": "testmixpanel" },
                },
            )

    def test_event_props(self):
        self._test_event('User logged in',
            properties={
                "distinct_id": "c9533b5b-d69e-479a-ae5f-42dd7a9752a0",
                "partner": True,
                "userid": 456,
                "code": "double oh 7",
                },
            data={
                "event": "User logged in",
                "properties": {
                    "distinct_id": "c9533b5b-d69e-479a-ae5f-42dd7a9752a0",
                    "partner": True,
                    "userid": 456,
                    "code": "double oh 7",
                    "token": "testmixpanel",
                    },
                },
            )

    def test_event_token(self):
        self._test_event('Override token',
            token="footoken",
            data={
                "event": "Override token",
                "properties": { "token": "footoken" },
                },
            )


class PeopleTrackerTest(TestCase):
    def _test_people(self, *args, **kwargs):
        kwargs.setdefault('endpoint', mp_settings.MIXPANEL_PEOPLE_TRACKING_ENDPOINT)
        return self._test_any(tasks.people_tracker, *args, **kwargs)

    def test_validation(self):
        self.assertRaises(tasks.InvalidPeopleProperties,
            tasks.people_tracker, 'foo')
        self.assertRaises(tasks.InvalidPeopleProperties,
            tasks.people_tracker, 'foo', set={1:2}, add={3:4})
        result = tasks.people_tracker('foo', set={1:2})
        self.assertEqual(result, True)
        result = tasks.people_tracker('foo', add={3:4})
        self.assertEqual(result, True)

    def test_people_set(self):
        self._test_people('c9533b5b-d69e-479a-ae5f-42dd7a9752a0',
            set={
                "$first_name": "Aron",
                },
            data={
                "$distinct_id": "c9533b5b-d69e-479a-ae5f-42dd7a9752a0",
                "$token": "testmixpanel",
                "$set": {
                    "$first_name": "Aron",
                    },
                })

    def test_people_add(self):
        self._test_people('c9533b5b-d69e-479a-ae5f-42dd7a9752a0',
            add={
                "visits": 1,
                },
            data={
                "$distinct_id": "c9533b5b-d69e-479a-ae5f-42dd7a9752a0",
                "$token": "testmixpanel",
                "$add": {
                    "visits": 1,
                    },
                })

    def test_people_token(self):
        self._test_people('c9533b5b-d69e-479a-ae5f-42dd7a9752a0',
            token="footoken",
            set={
                "$first_name": "Aron",
                },
            data={
                "$distinct_id": "c9533b5b-d69e-479a-ae5f-42dd7a9752a0",
                "$token": "footoken",
                "$set": {
                    "$first_name": "Aron",
                    },
                })

    def test_people_extra(self):
        self._test_people('c9533b5b-d69e-479a-ae5f-42dd7a9752a0',
            set={
                "$first_name": "Aron",
                },
            extra={
                "$ignore_time": True,
                },
            data={
                "$distinct_id": "c9533b5b-d69e-479a-ae5f-42dd7a9752a0",
                "$token": "testmixpanel",
                "$ignore_time": True,
                "$set": {
                    "$first_name": "Aron",
                    },
                })


class FunnelTrackerTest(TestCase):
    def _test_funnel(self, *args, **kwargs):
        return self._test_any(tasks.funnel_event_tracker, *args, **kwargs)

    def test_validation(self):
        funnel = 'test_funnel'
        step = 'test_step'
        goal = 'test_goal'

        # Missing distinct_id
        properties = {}
        self.assertRaises(tasks.InvalidFunnelProperties,
            tasks.funnel_event_tracker,
            funnel, step, goal, properties)

        # With distinct_id
        properties = {
            'distinct_id': 'c9533b5b-d69e-479a-ae5f-42dd7a9752a0',
            }
        result = tasks.funnel_event_tracker(funnel, step, goal, properties)
        self.assertEqual(result, True)

    def test_funnel(self):
        funnel = 'test_funnel'
        step = 'test_step'
        goal = 'test_goal'

        self._test_funnel(funnel, step, goal,
            properties={
                'distinct_id': 'c9533b5b-d69e-479a-ae5f-42dd7a9752a0',
                },
            data={
                "event": "mp_funnel",
                "properties": {
                    "distinct_id": "c9533b5b-d69e-479a-ae5f-42dd7a9752a0",
                    "funnel": "test_funnel",
                    "goal": "test_goal",
                    "step": "test_step",
                    "token": "testmixpanel"
                    },
                },
            )


class FailuresTestCase(TestCase):
    def test_failed_request(self):
        self.mock_urlopen.side_effect = urllib2.URLError("You're doing it wrong")

        # This wants to test RetryTaskError, but that isn't available with
        # CELERY_ALWAYS_EAGER
        self.assertRaises(tasks.FailedEventRequest, # RetryTaskError
                          tasks.event_tracker,
                          'event_foo')

    def test_failed_response(self):
        self.mock_urlopen.return_value.read.return_value = '0'
        result = tasks.event_tracker('event_foo')
        self.assertEqual(result, False)
