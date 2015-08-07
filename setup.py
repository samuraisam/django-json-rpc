#!/usr/bin/env python

import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

HERE = os.path.dirname(os.path.abspath(__file__))

setup(
  name="django-json-rpc",
  version="0.7.0",
  description="A simple JSON-RPC implementation for Django",
  long_description=open(os.path.join('README.mdown')).read(),
  author="Samuel Sutch",
  author_email="sam@sutch.net",
  license="MIT",
  url="http://github.com/samuraisam/django-json-rpc/tree/master",
  download_url="http://github.com/samuraisam/django-json-rpc/tree/master",
  classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules'],
  packages=['jsonrpc'],
  zip_safe = False, # we include templates and tests
  install_requires=['Django>=1.0', 'six'],
  package_data={'jsonrpc': ['templates/*']})
