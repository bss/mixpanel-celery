#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
import codecs
import os
import re
import sys

import mixpanel


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [dirpath
            for dirpath, dirnames, filenames in os.walk(package)
            if os.path.exists(os.path.join(dirpath, '__init__.py'))]


def get_package_data(package):
    """
    Return all files under the root package, that are not in a
    package themselves.
    """
    walk = [(dirpath.replace(package + os.sep, '', 1), filenames)
            for dirpath, dirnames, filenames in os.walk(package)
            if not os.path.exists(os.path.join(dirpath, '__init__.py'))]

    filepaths = []
    for base, filenames in walk:
        filepaths.extend([os.path.join(base, filename)
                          for filename in filenames])
    return {package: filepaths}


if sys.argv[-1] == 'publish':
    os.system("python setup.py sdist upload")
    args = {'version': get_version(package)}
    print "You probably want to also tag the version now:"
    print "  git tag -a %(version)s -m 'version %(version)s'" % args
    print "  git push --tags"
    sys.exit()


long_description = codecs.open("README.rst", "r", "utf-8").read()

setup(
    name='mixpanel-celery',
    version=mixpanel.__version__,
    description=mixpanel.__doc__,
    author=mixpanel.__author__,
    author_email=mixpanel.__contact__,
    url=mixpanel.__homepage__,
    platforms=['any'],
    license='BSD',
    packages=get_packages('mixpanel'),
    package_data=get_package_data('mixpanel'),
    scripts=[],
    zip_safe=False,
    install_requires=['celery>=3.0', 'django>=1.3'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Django",
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    long_description=long_description,
)
