===========================================================
 mixpanel-celery - Asynchronous event tracking for Mixpanel
===========================================================

:Version: |release|

Introduction
============

mixpanel-celery helps you use `Celery`_ to asynchronously track your `Mixpanel`_
events. You want to perform your tracking asynchronously, because waiting for HTTP
requests to Mixpanel to complete every time you want to record something important
isn't ideal when you've already worked so hard to tune your performance.

Installation
============

The easiest way to install the current development version of mixpanel-celery is
via `pip`_

Installing The Stable Version
-----------------------------

.. code-block:: bash

    $ pip install mixpanel-celery


Installing The Development Version
----------------------------------

.. code-block:: bash

    $ pip install -e git+git://github.com/winhamwr/mixpanel-celery.git#egg=mixpanel-celery

Running The Test Suite
======================

Setuptools' ``nosetests`` command is the easiest way to run the test suite.

.. code-block:: bash

    $ cd /path/to/mixpanel-celery
    $ python setup.py nosetests

Currently, two tests will fail unless you configure `RabbitMQ`_ specifically for
the test suite.

It is also possible to run specific tests, disable coverage, use
``--multiprocess``, etc. by using the ``scripts/run_tests.py`` script. For
example, to only run a  single test

.. code-block:: bash

    $ cd /path/to/mixpanel-celery/scripts
    $ ./run_tests.py mixpanel.test.test_tasks:EventTrackerTest.test_handle_properties_no_token

Configuration
=============

Configure `Celery`_ as usual, use tasks as seen below.

Usage
=====

Basic python example tracking an event called ``my_event``

.. code-block:: python

    from mixpanel.tasks import event_tracker

    event_tracker.delay('my_event', {'distinct_id': 1}, token='YOUR_API_TOKEN')


Building the Documentation
==========================

mixpanel-celery uses `sphinx`_ for documentation. To build the HTML docs

.. code-block:: bash

    $ pip install sphinx
    $ pip install sphinxtogithub
    $ cd /path/to/mixpanel-celery/docs
    $ make html

Bug Tracker
===========

If you have feedback about bugs, features or anything else, the github issue
tracking is a great place to report them:
http://github.com/bss/mixpanel-celery/issues

License
=======

This software is licensed under the ``New BSD License``. See the ``LICENSE``
file in the top distribution directory for the full license text.

Versioning
==========

This project uses `Semantic Versioning`_.

.. _`Celery`: http://ask.github.com/celery/
.. _`Mixpanel`: http://mixpanel.com/
.. _`sphinx`: http://sphinx.pocoo.org/
.. _`online mixpanel-celery documentation`: http://winhamwr.github.com/mixpanel-celery/
.. _`Semantic Versioning`: http://semver.org/
.. _`pip`: http://pypi.python.org/pypi/pip
.. _`RabbitMQ`: http://www.rabbitmq.com/