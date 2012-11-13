#!/usr/bin/env python
import os
import sys


# Work around strptime threading issue, see http://bugs.python.org/issue7980
import time
time.strptime("9/9/2010", "%m/%d/%Y")


def main(args):
    if args[1] in ['test', 'harvest']:
        # Prevent network requests while running unit tests.
        prevent_network_calls()

    from django.core.management import execute_from_command_line
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testsettings")
    execute_from_command_line(args)


def prevent_network_calls():
    import urllib, urllib2
    def no_network_while_testing(*args, **kwargs):
        raise urllib2.URLError('No networking while testing')
    urllib.urlretrieve, urllib.real_urlretrieve = (
        no_network_while_testing, urllib.urlretrieve)
    urllib2.urlopen, urllib2.real_urlopen = (
        no_network_while_testing, urllib2.urlopen)
    urllib2.build_opener, urllib2.real_build_opener = (
        no_network_while_testing, urllib2.build_opener)


if __name__ == "__main__":
    main(sys.argv)
