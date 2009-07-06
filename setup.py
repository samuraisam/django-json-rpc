#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
  name="django-json-rpc",
  version="0.1",
  description="A simple JSON-RPC implementation for Django",
  author="Samuel Sutch",
  author_email="samuraiblog@gmail.com",
  license="MIT",
  url="http://github.com/samuraisam/django-json-rpc/tree/master",
  download_url="http://github.com/samuraisam/django-json-rpc/tree/master",
  classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules'],
  packages=['jsonrpc'])