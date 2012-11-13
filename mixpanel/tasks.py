from __future__ import absolute_import

import urllib
import urllib2
import base64
import copy

from celery.task import task
from celery.utils.log import get_task_logger
log = get_task_logger(__name__)

from django.utils import simplejson

from .conf import settings as mp_settings

@task(max_retries=mp_settings.MIXPANEL_MAX_RETRIES)
def people_tracker(distinct_id, properties=None, token=None):
    """
    Send people analytics to mixpanel through the API.

    ``distinct_id`` is the user's distinct id.
    ``properties`` is a dict of key/value pairs (optional).
    ``token`` overrides MIXPANEL_API_TOKEN (optional).
    """
    log.info("Recording person: %r" % distinct_id)

    props = _build_props(properties, token)

    url_params = _build_people_params(distinct_id, props)

    try:
        result = _send_request(url_params, mp_settings.MIXPANEL_PEOPLE_TRACKING_ENDPOINT)
    except FailedEventRequest as e:
        log.info("Event failed. Retrying: user <%s>" % distinct_id)
        raise people_tracker.retry(exc=e, countdown=mp_settings.MIXPANEL_RETRY_DELAY)
    return result

@task(max_retries=mp_settings.MIXPANEL_MAX_RETRIES)
def event_tracker(event_name, properties=None, token=None):
    """
    Track an event occurrence to mixpanel through the API.

    ``event_name`` is the event name to record.
    ``properties`` is a dict of key/value pairs (optional).
    ``token`` overrides MIXPANEL_API_TOKEN (optional).
    """
    log.info("Recording event: <%s>" % event_name)

    props = _build_props(properties, token)

    url_params = _build_params(event_name, props)

    try:
        result = _send_request(url_params)
    except FailedEventRequest as e:
        log.info("Event failed. Retrying: %r" % event_name)
        raise event_tracker.retry(exc=e, countdown=mp_settings.MIXPANEL_RETRY_DELAY)
    return result

@task(max_retries=mp_settings.MIXPANEL_MAX_RETRIES)
def funnel_event_tracker(funnel, step, goal, properties, token=None):
    """
    Track an event occurrence to mixpanel through the API.

    ``funnel`` is funnel name for this event.
    ``step`` is the step in the funnel.
    ``goal`` is the final step in the funnel.
    ``properties`` is a dict of key/value pairs which must contain ``distinct_id``.
    ``token`` overrides MIXPANEL_API_TOKEN (optional).
    """
    log.info("Recording funnel: %r, step: %r" % (funnel, step))

    props = _build_props(properties, token)
    props = _add_funnel_props(props, funnel, step, goal)

    url_params = _build_params(mp_settings.MIXPANEL_FUNNEL_EVENT_ID, props)

    try:
        result = _send_request(url_params)
    except FailedEventRequest as e:
        log.info("Funnel failed. Retrying: %r, step: %r" % (funnel, step))
        raise funnel_event_tracker.retry(exc=e, countdown=mp_settings.MIXPANEL_RETRY_DELAY)
    return result

class FailedEventRequest(Exception):
    """The attempted recording event failed because of a non-200 HTTP return code"""

class InvalidFunnelProperties(Exception):
    """Required properties were missing from the funnel-tracking call"""

def _build_props(props, token):
    """
    Returns a new props dictionary including token.
    """
    props = dict(props or {})
    props.setdefault('token', token or mp_settings.MIXPANEL_API_TOKEN)
    return props

def _build_people_params(distinct_id, properties):
    """
    Build HTTP params to record the given event and properties.
    """
    props = copy.deepcopy(properties)
    token = props.pop('token', mp_settings.MIXPANEL_API_TOKEN)
    params = {'$distinct_id': distinct_id, '$token': token}
    if 'set' in props:
        #adding $ to any reserved mixpanel vars
        for special_prop in mp_settings.MIXPANEL_RESERVED_PEOPLE_PROPERTIES:
            if special_prop in props['set']:
                props['set']['${}'.format(special_prop)] = props['set'][special_prop]
                del props['set'][special_prop]
        params['$set'] = props['set']
    if 'increment' in props:
        params['$add'] = props['increment']
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

def _add_funnel_props(props, funnel, step, goal):
    """
    Returns a new props dictionary including funnel properties.
    """
    props = dict(props or {})
    if 'distinct_id' not in props:
        raise InvalidFunnelProperties("distinct_id required for funnel event")
    props.update(dict(
        funnel=funnel,
        step=step,
        goal=goal,
        ))
    return props
