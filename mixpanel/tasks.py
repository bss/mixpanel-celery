from __future__ import absolute_import

import urllib
import urllib2
import base64
import copy

from celery.task import task
from celery.utils.log import get_task_logger
log = get_task_logger(__name__)

import simplejson

from .conf import settings as mp_settings

@task(max_retries=mp_settings.MIXPANEL_MAX_RETRIES)
def people_tracker(distinct_id, set=None, add=None, extra=None, token=None):
    """
    Sends people analytics to mixpanel through the API.
    Returns True if mixpanel accepted the request.

    ``distinct_id`` is the user's distinct id.
    ``set`` is a dict of people values to set.
    ``add`` is a dict of people values to increment.
    ``extra`` is top-level params to add to the generated dict.
    ``token`` overrides MIXPANEL_API_TOKEN (optional).
    """
    log.info("Recording person: %r" % distinct_id)

    params = _build_people_params(distinct_id, set, add, token)
    params.update(extra or {})

    try:
        result = _send_request(params, mp_settings.MIXPANEL_PEOPLE_TRACKING_ENDPOINT)
    except FailedEventRequest as e:
        log.info("Event failed. Retrying: user <%s>" % distinct_id)
        raise people_tracker.retry(exc=e, countdown=mp_settings.MIXPANEL_RETRY_DELAY)
    return result

@task(max_retries=mp_settings.MIXPANEL_MAX_RETRIES)
def event_tracker(event_name, properties=None, token=None):
    """
    Tracks an event occurrence to mixpanel through the API.
    Returns True if mixpanel accepted the request.

    ``event_name`` is the event name to record.
    ``properties`` is a dict of key/value pairs (optional).
    ``token`` overrides MIXPANEL_API_TOKEN (optional).
    """
    log.info("Recording event: <%s>" % event_name)

    props = _build_props(properties, token)
    params = {'event': event_name, 'properties': props}

    try:
        result = _send_request(params)
    except FailedEventRequest as e:
        log.info("Event failed. Retrying: %r" % event_name)
        raise event_tracker.retry(exc=e, countdown=mp_settings.MIXPANEL_RETRY_DELAY)
    return result

@task(max_retries=mp_settings.MIXPANEL_MAX_RETRIES)
def funnel_event_tracker(funnel, step, goal, properties, token=None):
    """
    Tracks an event occurrence to mixpanel through the API.
    Returns True if mixpanel accepted the request.

    ``funnel`` is funnel name for this event.
    ``step`` is the step in the funnel.
    ``goal`` is the final step in the funnel.
    ``properties`` is a dict of key/value pairs which must contain ``distinct_id``.
    ``token`` overrides MIXPANEL_API_TOKEN (optional).
    """
    log.info("Recording funnel: %r, step: %r" % (funnel, step))

    props = _build_props(properties, token)
    props = _add_funnel_props(props, funnel, step, goal)
    params = {'event': mp_settings.MIXPANEL_FUNNEL_EVENT_ID, 'properties': props}

    try:
        result = _send_request(params)
    except FailedEventRequest as e:
        log.info("Funnel failed. Retrying: %r, step: %r" % (funnel, step))
        raise funnel_event_tracker.retry(exc=e, countdown=mp_settings.MIXPANEL_RETRY_DELAY)
    return result

class FailedEventRequest(Exception):
    """The attempted recording event failed because of a non-200 HTTP return code"""

class InvalidFunnelProperties(Exception):
    """Required properties were missing from the funnel-tracking call"""

class InvalidPeopleProperties(Exception):
    """Invalid combination of people properties"""

def _build_props(props, token):
    """
    Returns a new props dictionary including token.
    """
    props = dict(props or {})
    props.setdefault('token', token or mp_settings.MIXPANEL_API_TOKEN)
    return props

def _build_people_params(distinct_id, set, add, token):
    """
    Returns a new params dictionary appropriate for people tracking.
    """
    if not set and not add:
        raise InvalidPeopleProperties("People analytics requires either $set or $add")
    if set and add:
        raise InvalidPeopleProperties("Mixpanel requires $set or $add, not both")

    params = {}
    params['$distinct_id'] = distinct_id
    params['$token'] = token or mp_settings.MIXPANEL_API_TOKEN
    if set:
        params['$set'] = dict(set)
    else:
        params['$add'] = dict(add)
    return params

def _send_request(params, endpoint=mp_settings.MIXPANEL_TRACKING_ENDPOINT):
    """
    Sends a an event with its properties to the api server.
    Returns True if the event was logged by Mixpanel else False.
    """
    data = base64.b64encode(simplejson.dumps(params))
    querystring = urllib.urlencode({mp_settings.MIXPANEL_DATA_VARIABLE: data})
    url = 'https://%s%s?%s' % (mp_settings.MIXPANEL_API_SERVER, endpoint, querystring)
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
