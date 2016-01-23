import os
import sys
import unittest
import time
import urllib
import threading
import six
from six.moves.urllib import request as urllib_request
from six.moves.urllib import parse as urllib_parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

TEST_DEFAULTS = {
  'ROOT_URLCONF': 'jsontesturls',
  'DEBUG': True,
  'DEBUG_PROPAGATE_EXCEPTIONS': True,
  'DATETIME_FORMAT': 'N j, Y, P',
  'USE_I18N': False,
  'INSTALLED_APPS': (
    'jsonrpc',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions'),
  'DATABASES': {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.sqlite3',
      },
  },
  'MIDDLEWARE_CLASSES': (
      'django.middleware.common.CommonMiddleware',
      'django.contrib.sessions.middleware.SessionMiddleware',
      'django.middleware.csrf.CsrfViewMiddleware',
      'django.contrib.auth.middleware.AuthenticationMiddleware',
  ),
  'AUTHENTICATION_BACKENDS': ('django.contrib.auth.backends.ModelBackend',),
  'TEMPLATE_LOADERS': (
      'django.template.loaders.filesystem.load_template_source',
      'django.template.loaders.app_directories.load_template_source'),
}

from django.conf import settings
settings.configure(**TEST_DEFAULTS)

import django
if hasattr(django, 'setup'):
  # Run django.setup() for Django>=1.7
  django.setup()

from django.core import management
from django.test import Client
from django.contrib.auth.models import User
from jsonrpc import jsonrpc_method, _parse_sig, Any
from jsonrpc.proxy import ServiceProxy, TestingServiceProxy
from jsonrpc._json import loads, dumps
from jsonrpc.site import validate_params
from jsonrpc.exceptions import *
from jsonrpc._types import *

try:
  from collections import OrderedDict
except ImportError:
  # Use SortedDict instead of OrderedDict for python < 2.7
  # Can be removed when support for Django < 1.7 is dropped
  # https://docs.djangoproject.com/en/1.7/releases/1.7/#django-utils-datastructures-sorteddict
  from django.utils.datastructures import SortedDict as OrderedDict


def _call(host, req):
  return loads(urllib_request.urlopen(host, dumps(req).encode('utf-8')).read().decode('utf-8'))


def start_json_server_thread():
  class JSONServer(object):
    def _thread_body(self):
      try:
        from wsgiref.simple_server import make_server
        from django.core.handlers.wsgi import WSGIHandler
        import django
        ver = django.VERSION[:2]
        if ver >= (1, 7):
          django.setup() # populate app registry for django >= 1.8

        if ver <= (1, 7):
          management.call_command('syncdb', interactive=False)
        else:
          management.call_command('migrate', interactive=False)
        try:
          User.objects.create_user(username='sammeh', email='sam@rf.com', password='password').save()
        except:
          pass

        http = make_server('', 8999, WSGIHandler())
        print('Server made. continue={0}'.format(self.continue_serving))
        self.event.set() # notify parent thread that the server is ready to serve requests
        while self.continue_serving:
          print('Waiting for request!')
          http.handle_request()
          self.n_requests += 1
          print('Handled {0} requests!'.format(self.n_requests))
        print('Got server stop! requests={0}'.format(self.n_requests))
        http.server_close()
        print('Server closed!')
      except Exception as e:
        import traceback
        traceback.print_exc()
        print('Error startign server: {0}'.format(e))
      finally:
        if not self.event.is_set():
          self.event.set()

    def start(self):
      print('Got server start')
      self.continue_serving = True
      self.n_requests = 0
      self.event = threading.Event()
      self.t = threading.Thread(target=self._thread_body)
      self.t.start()
      self.event.wait()
      return self

    def stop(self):
      print('Got stop call')
      self.continue_serving = False
      try:
        proxy = ServiceProxy('http://127.0.0.1:8999/json/', version=2.0)
        proxy.jsonrpc.test(string='Hello')['result']
      except: # doesnt matter if this fails
        pass
      self.t.join(2.0)
      return self

  return JSONServer().start()


class JSONServerTestCase(unittest.TestCase):
  def setUp(self):
    self.host = 'http://127.0.0.1:8999/json/'

@jsonrpc_method('jsonrpc.test')
def echo(request, string):
  """Returns whatever you give it."""
  return string

@jsonrpc_method('jsonrpc.testAuth', authenticated=True)
def echoAuth(requet, string):
  return string

@jsonrpc_method('jsonrpc.notify')
def notify(request, string):
  pass

@jsonrpc_method('jsonrpc.fails')
def fails(request, string):
  raise IndexError

@jsonrpc_method('jsonrpc.strangeEcho')
def strangeEcho(request, string, omg, wtf, nowai, yeswai='Default'):
  return [string, omg, wtf, nowai, yeswai]

@jsonrpc_method('jsonrpc.safeEcho', safe=True)
def safeEcho(request, string):
  return string

@jsonrpc_method('jsonrpc.strangeSafeEcho', safe=True)
def strangeSafeEcho(request, *args, **kwargs):
  return strangeEcho(request, *args, **kwargs)

@jsonrpc_method('jsonrpc.checkedEcho(string=str, string2=str) -> str', safe=True, validate=True)
def protectedEcho(request, string, string2):
  return string + string2

@jsonrpc_method('jsonrpc.checkedArgsEcho(string=str, string2=str)', validate=True)
def protectedArgsEcho(request, string, string2):
  return string + string2

@jsonrpc_method('jsonrpc.checkedReturnEcho() -> String', validate=True)
def protectedReturnEcho(request, string, string2):
  return string + string2

@jsonrpc_method('jsonrpc.authCheckedEcho(Object, Array) -> Object', validate=True)
def authCheckedEcho(request, obj1, arr1):
  return {'obj1': obj1, 'arr1': arr1}

@jsonrpc_method('jsonrpc.varArgs(String, String, str3=String) -> Array', validate=True)
def checkedVarArgsEcho(request, *args, **kw):
  return list(args) + list(kw.values())

@jsonrpc_method('jsonrpc.tuple() -> Array', validate=True)
def returnTuple(request):
    return 1, 0


class JSONRPCFunctionalTests(unittest.TestCase):
  def test_method_parser(self):
    working_sigs = [
      ('jsonrpc', 'jsonrpc', OrderedDict(), Any),
      ('jsonrpc.methodName', 'jsonrpc.methodName', OrderedDict(), Any),
      ('jsonrpc.methodName() -> list', 'jsonrpc.methodName', OrderedDict(), list),
      ('jsonrpc.methodName(str, str, str ) ', 'jsonrpc.methodName', OrderedDict([('a', str), ('b', str), ('c', str)]), Any),
      ('jsonrpc.methodName(str, b=str, c=str)', 'jsonrpc.methodName', OrderedDict([('a', str), ('b', str), ('c', str)]), Any),
      ('jsonrpc.methodName(str, b=str) -> dict', 'jsonrpc.methodName', OrderedDict([('a', str), ('b', str)]), dict),
      ('jsonrpc.methodName(str, str, c=Any) -> Any', 'jsonrpc.methodName', OrderedDict([('a', str), ('b', str), ('c', Any)]), Any),
      ('jsonrpc(Any ) ->  Any', 'jsonrpc', OrderedDict([('a', Any)]), Any),
    ]
    error_sigs = [
      ('jsonrpc(str) -> nowai', ValueError),
      ('jsonrpc(nowai) -> Any', ValueError),
      ('jsonrpc(nowai=str, str)', ValueError),
      ('jsonrpc.methodName(nowai*str) -> Any', ValueError)
    ]
    for sig in working_sigs:
      ret = _parse_sig(sig[0], list(iter(sig[2])))
      self.assertEquals(ret[0], sig[1])
      self.assertEquals(ret[1], sig[2])
      self.assertEquals(ret[2], sig[3])
    for sig in error_sigs:
      e = None
      try:
        _parse_sig(sig[0], ['a'])
      except Exception as exc:
        e = exc
      self.assert_(type(e) is sig[1])

  def test_validate_args(self):
    sig = 'jsonrpc(String, String) -> String'
    M = jsonrpc_method(sig, validate=True)(lambda r, s1, s2: s1+s2)
    self.assert_(validate_params(M, {'params': ['omg', 'wtf']}) is None)

    E = None
    try:
      validate_params(M, {'params': [['omg'], ['wtf']]})
    except Exception as e:
      E = e
    self.assert_(type(E) is InvalidParamsError)

  def test_validate_args_any(self):
    sig = 'jsonrpc(s1=Any, s2=Any)'
    M = jsonrpc_method(sig, validate=True)(lambda r, s1, s2: s1+s2)
    self.assert_(validate_params(M, {'params': ['omg', 'wtf']}) is None)
    self.assert_(validate_params(M, {'params': [['omg'], ['wtf']]}) is None)
    self.assert_(validate_params(M, {'params': {'s1': 'omg', 's2': 'wtf'}}) is None)

  def test_types(self):
    if six.PY2:
      assert type(unicode('')) == String
    assert type('') == String
    assert not type('') == Object
    assert not type([]) == Object
    assert type([]) == Array
    assert type('') == Any
    assert Any.kind('') == String
    assert Any.decode('str') == String
    assert Any.kind({}) == Object
    assert Any.kind(None) == Nil
    assert type(1) == Number
    assert type(1.1) == Number


class ServiceProxyTest(JSONServerTestCase):
  def test_positional_args(self):
    proxy = ServiceProxy(self.host)
    self.assert_(proxy.jsonrpc.test('Hello')['result'] == 'Hello')
    try:
      proxy.jsonrpc.test(string='Hello')
    except Exception as e:
      self.assert_(e.args[0] == 'Unsupported arg type for JSON-RPC 1.0 '
                                '(the default version for this client, '
                                'pass version="2.0" to use keyword arguments)')
    else:
      self.assert_(False, 'Proxy didnt warn about version mismatch')

  def test_keyword_args(self):
    proxy = ServiceProxy(self.host, version='2.0')
    self.assert_(proxy.jsonrpc.test(string='Hello')['result'] == 'Hello')
    self.assert_(proxy.jsonrpc.test('Hello')['result'] == 'Hello')

  def test_testing_proxy(self):
    client = Client()
    proxy = TestingServiceProxy(client, self.host, version='2.0')
    self.assert_(proxy.jsonrpc.test(string='Hello')['result'] == 'Hello')
    self.assert_(proxy.jsonrpc.test('Hello')['result'] == 'Hello')


class JSONRPCTest(JSONServerTestCase):
  def setUp(self):
    super(JSONRPCTest, self).setUp()
    self.proxy10 = ServiceProxy(self.host, version='1.0')
    self.proxy20 = ServiceProxy(self.host, version='2.0')

  def test_10(self):
    self.assertEqual(
      self.proxy10.jsonrpc.test('this is a string')['result'],
      'this is a string')

  def test_11(self):
    req = {
      'version': '1.1',
      'method': 'jsonrpc.test',
      'params': ['this is a string'],
      'id': 'holy-mother-of-god'
    }
    resp = _call(self.host, req)
    self.assertEquals(resp['id'], req['id'])
    self.assertEquals(resp['result'], req['params'][0])

  def test_10_notify(self):
    pass

  def test_11_positional_mixed_args(self):
    req = {
      'version': '1.1',
      'method': 'jsonrpc.strangeEcho',
      'params': {'1': 'this is a string', '2': 'this is omg',
                  'wtf': 'pants', 'nowai': 'nopants'},
      'id': 'toostrange'
    }
    resp = _call(self.host, req)
    self.assertEquals(resp['result'][-1], 'Default')
    self.assertEquals(resp['result'][1], 'this is omg')
    self.assertEquals(resp['result'][0], 'this is a string')
    self.assert_('error' not in resp)

  def test_11_GET(self):
    pass

  def test_11_GET_unsafe(self):
    pass

  def test_11_GET_mixed_args(self):
    params = {'1': 'this is a string', '2': 'this is omg',
              'wtf': 'pants', 'nowai': 'nopants'}
    url = "%s%s?%s" % (
      self.host, 'jsonrpc.strangeSafeEcho',
      (''.join(['%s=%s&' % (k, urllib_parse.quote(v)) for k, v in params.items()])).rstrip('&')
    )
    resp = loads(urllib_request.urlopen(url).read().decode('utf-8'))
    self.assertEquals(resp['result'][-1], 'Default')
    self.assertEquals(resp['result'][1], 'this is omg')
    self.assertEquals(resp['result'][0], 'this is a string')
    self.assert_('error' not in resp)

  def test_20_checked(self):
    self.assertEqual(
      self.proxy10.jsonrpc.varArgs('o', 'm', 'g')['result'],
      ['o', 'm', 'g']
    )
    self.assert_(self.proxy10.jsonrpc.varArgs(1,2,3)['error'])

  def test_11_service_description(self):
    pass

  def test_20_keyword_args(self):
    self.assertEqual(
      self.proxy20.jsonrpc.test(string='this is a string')['result'],
      'this is a string')

  def test_20_positional_args(self):
    self.assertEqual(
      self.proxy20.jsonrpc.test('this is a string')['result'],
      'this is a string')

  def test_20_notify(self):
    req = {
      'jsonrpc': '2.0',
      'method': 'jsonrpc.notify',
      'params': ['this is a string'],
      'id': None
    }
    resp = urllib_request.urlopen(self.host, dumps(req).encode('utf-8')).read().decode('utf-8')
    self.assertEquals(resp, '')

  def test_20_batch(self):
    req = [{
      'jsonrpc': '2.0',
      'method': 'jsonrpc.test',
      'params': ['this is a string'],
      'id': 'id-'+str(i)
    } for i in range(5)]
    resp = loads(urllib_request.urlopen(self.host, dumps(req).encode('utf-8')).read().decode('utf-8'))
    self.assertEquals(len(resp), len(req))
    for i, D in enumerate(resp):
      self.assertEquals(D['result'], req[i]['params'][0])
      self.assertEquals(D['id'], req[i]['id'])

  def test_20_batch_with_errors(self):
    req = [{
      'jsonrpc': '2.0',
      'method': 'jsonrpc.test' if not i % 2 else 'jsonrpc.fails',
      'params': ['this is a string'],
      'id': 'id-'+str(i)
    } for i in range(10)]
    resp = loads(urllib_request.urlopen(self.host, dumps(req).encode('utf-8')).read().decode('utf-8'))
    self.assertEquals(len(resp), len(req))
    for i, D in enumerate(resp):
      if not i % 2:
        self.assertEquals(D['result'], req[i]['params'][0])
        self.assertEquals(D['id'], req[i]['id'])
        self.assert_('error' not in D)
      else:
        self.assert_('result' not in D)
        self.assert_('error' in D)
        self.assertEquals(D['error']['code'], 500)

  def test_authenticated_ok(self):
    self.assertEquals(
      self.proxy10.jsonrpc.testAuth(
        'sammeh', 'password', 'this is a string')['result'],
      'this is a string')

  def test_authenticated_ok_kwargs(self):
    self.assertEquals(
      self.proxy20.jsonrpc.testAuth(
        username='sammeh', password='password', string='this is a string')['result'],
      'this is a string')

  def test_authenticated_fail_kwargs(self):
    try:
      self.proxy20.jsonrpc.testAuth(
        username='osammeh', password='password', string='this is a string')
    except IOError as e:
      self.assertEquals(e.args[1], 401)
    else:
      self.assert_(False, 'Didnt return status code 401 on unauthorized access')

  def test_authenticated_fail(self):
    try:
      self.proxy10.jsonrpc.testAuth(
        'osammeh', 'password', 'this is a string')
    except IOError as e:
      self.assertEquals(e.args[1], 401)
    else:
      self.assert_(False, 'Didnt return status code 401 on unauthorized access')

  def test_authenticated_insufficient_kwargs(self):
    """
    Test method with required authentication with insufficient keyword arguments.
    """

    resp = self.proxy20.jsonrpc.testAuth(string='this is a string')

    # Expected: InvalidParamsError (code -32602)
    self.assert_('result' not in resp)
    self.assertEquals(resp['error']['code'], -32602)

  def test_authenticated_insufficient_args(self):
    """
    Test method with required authentication with insufficient arguments.
    """
    resp = self.proxy10.jsonrpc.testAuth('this is a string')

    # Expected: InvalidParamsError (code -32602)
    self.assertEquals(resp['result'], None)
    self.assertEquals(resp['error']['code'], -32602)

  def test_return_tuple_10(self):
    resp = self.proxy10.jsonrpc.tuple()

    self.assertEqual(resp['result'], [1, 0])

  def test_return_tuple_20(self):
    resp = self.proxy20.jsonrpc.tuple()

    self.assertEqual(resp['result'], [1, 0])


if __name__ == '__main__':
  server = None
  if os.path.exists('test.sqlite3'):
    os.remove('test.sqlite3')
  try:
    server = start_json_server_thread()
    unittest.main(argv=sys.argv)
  finally:
    if server:
      server.stop()
    if os.path.exists('test.sqlite3'):
      os.remove('test.sqlite3')
