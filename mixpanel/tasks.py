from __future__ import absolute_import

import urllib
import urllib2
import base64

from celery.task import task
from celery.utils.log import get_task_logger
log = get_task_logger(__name__)

from django.utils import simplejson

from .conf import settings as mp_settings

@task(name="mixpanel.tasks.PeopleTracker", max_retries=mp_settings.MIXPANEL_MAX_RETRIES)
def people_tracker(distinct_id, properties=None, token=None, throw_retry_error=False):
    """
    Track an event occurrence to mixpanel through the API.

    ``event_name`` is the string for the event/category you'd like to log
    this event under
    ``properties`` is (optionally) a dictionary of key/value pairs
    describing the event.
    ``token`` is (optionally) your Mixpanel api token. Not required if
    you've already configured your MIXPANEL_API_TOKEN setting.
    """
    log.info("Recording people datapoint: <%s>" % distinct_id)

    url_params = _build_people_params(distinct_id, properties)

    try:
        result = _send_request(url_params, mp_settings.MIXPANEL_PEOPLE_TRACKING_ENDPOINT)
    except FailedEventRequest, exception:
        log.info("Event failed. Retrying: user <%s>" % distinct_id)
        raise event_tracker.retry(exc=exception,
            countdown=mp_settings.MIXPANEL_RETRY_DELAY,
            throw=throw_retry_error)
    return result

@task(name="mixpanel.tasks.EventTracker", max_retries=mp_settings.MIXPANEL_MAX_RETRIES)
def event_tracker(event_name, properties=None, token=None, throw_retry_error=False):
    """
    Track an event occurrence to mixpanel through the API.

    ``event_name`` is the string for the event/category you'd like to log
    this event under
    ``properties`` is (optionally) a dictionary of key/value pairs
    describing the event.
    ``token`` is (optionally) your Mixpanel api token. Not required if
    you've already configured your MIXPANEL_API_TOKEN setting.
    """
    log.info("Recording event: <%s>" % event_name)

    generated_properties = _handle_properties(properties, token)

    url_params = _build_params(event_name, generated_properties)

    try:
        result = _send_request(url_params)
    except FailedEventRequest, exception:
        log.info("Event failed. Retrying: <%s>" % event_name)
        raise event_tracker.retry(exc=exception,
                   countdown=mp_settings.MIXPANEL_RETRY_DELAY,
                   throw=throw_retry_error)
    return result

@task(name="mixpanel.tasks.FunnelEventTracker", max_retries=mp_settings.MIXPANEL_MAX_RETRIES)
def funnel_event_tracker(funnel, step, goal, properties, token=None, throw_retry_error=False):
    """
    Track an event occurrence to mixpanel through the API.

    ``funnel`` is the string for the funnel you'd like to log
    this event under
    ``step`` the step in the funnel you're registering
    ``goal`` the end goal of this funnel
    ``properties`` is a dictionary of key/value pairs
    describing the funnel event. A ``distinct_id`` is required.
    ``token`` is (optionally) your Mixpanel api token. Not required if
    you've already configured your MIXPANEL_API_TOKEN setting.
    """
    log.info("Recording funnel: <%s>-<%s>" % (funnel, step))
    properties = _handle_properties(properties, token)

    properties = _add_funnel_properties(properties, funnel, step, goal)

    url_params = _build_params(mp_settings.MIXPANEL_FUNNEL_EVENT_ID, properties)

    try:
        result = _send_request(url_params)
    except FailedEventRequest, exception:
        log.info("Funnel failed. Retrying: <%s>-<%s>" % (funnel, step))
        raise funnel_event_tracker.retry(exc=exception,
                   countdown=mp_settings.MIXPANEL_RETRY_DELAY,
                   throw=throw_retry_error)
    return result

class FailedEventRequest(Exception):
    """The attempted recording event failed because of a non-200 HTTP return code"""
    pass

class InvalidFunnelProperties(Exception):
    """Required properties were missing from the funnel-tracking call"""
    pass

def _handle_properties(properties, token):
    """
    Build a properties dictionary, accounting for the token.
    """
    if properties == None:
        properties = {}

    if not properties.get('token', None):
        if token is None:
            token = mp_settings.MIXPANEL_API_TOKEN
        properties['token'] = token

    return properties

def _build_people_params(distinct_id, properties):
    """
    Build HTTP params to record the given event and properties.
    """
    params = {'$distinct_id': distinct_id,'$token': mp_settings.MIXPANEL_API_TOKEN}
    if 'set' in properties:
        #adding $ to any reserved mixpanel vars
        for special_prop in mp_settings.MIXPANEL_RESERVED_PEOPLE_PROPERTIES:
            if special_prop in properties['set']:
                properties['set']['${}'.format(special_prop)] = properties['set'][special_prop]
                del properties['set'][special_prop]
        params['$set'] = properties['set']
    if 'increment' in properties:
        params['$add'] = properties['increment']
    data = base64.b64encode(simplejson.dumps(params))

    data_var = mp_settings.MIXPANEL_DATA_VARIABLE
    url_params = urllib.urlencode({data_var: data})

    return url_params

def _build_params(event, properties):
    """
    Build HTTP params to record the given event and properties.
    """
    params = {'event': event, 'properties': properties}
    data = base64.b64encode(simplejson.dumps(params))

    data_var = mp_settings.MIXPANEL_DATA_VARIABLE
    url_params = urllib.urlencode({data_var: data})

    return url_params

def _send_request(params, endpoint=mp_settings.MIXPANEL_TRACKING_ENDPOINT):
    """
    Send a an event with its properties to the api server.

    Returns ``true`` if the event was logged by Mixpanel.
    """
    url = 'https://%s%s?%s' % (mp_settings.MIXPANEL_API_SERVER, endpoint, params)
    try:
        response = urllib2.urlopen(url, None, mp_settings.MIXPANEL_API_TIMEOUT)
    except urllib2.URLError as e:
        raise FailedEventRequest("Tracking request failed: %s" % e)

    # Successful request gets a single-byte response of "1" from mixpanel
    return response.read() == '1'

def _add_funnel_properties(properties, funnel, step, goal):
    if not 'distinct_id' in properties:
        error_msg = "A ``distinct_id`` must be given to record a funnel event"
        raise InvalidFunnelProperties(error_msg)
    properties['funnel'] = funnel
    properties['step'] = step
    properties['goal'] = goal

    return properties

