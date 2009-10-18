import os
import sys
import unittest
import subprocess
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
TEST_DEFAULTS = {
  'ROOT_URLCONF': 'jsontesturls',
  'DEBUG': True,
  'DEBUG_PROPAGATE_EXCEPTIONS': True,
  'DATETIME_FORMAT': 'N j, Y, P',
  'USE_I18N': False
}
from django.conf import settings
settings.configure(**TEST_DEFAULTS)

from jsonrpc import jsonrpc_method
from jsonrpc.proxy import ServiceProxy
from jsonrpc.site import json


def json_serve_thread():
  from wsgiref.simple_server import make_server
  from django.core.handlers.wsgi import WSGIHandler
  http = make_server('', 8999, WSGIHandler())
  http.serve_forever()

@jsonrpc_method('jsonrpc.test')
def echo(request, string):
  return string


class JSONRPCTest(unittest.TestCase):
  def setUp(self):
    self.proc = subprocess.Popen(['python', 
      os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test.py')])
    self.host = 'http://127.0.0.1:8999/json/'
    self.proxy10 = ServiceProxy(self.host, version='1.0')
    self.proxy20 = ServiceProxy(self.host, version='2.0')
  
  def tearDown(self):
    self.proc.terminate()
    self.proc.wait()
  
  def test_10(self):
    self.assertEqual(
      self.proxy10.jsonrpc.test('this is a string')[u'result'], 
      u'this is a string')
  
  def test_20_kw(self):
    self.assertEqual(
      self.proxy20.jsonrpc.test(string='this is a string')[u'result'],
      u'this is a string')
  
  def test_20_pos(self):
    self.assertEqual(
      self.proxy20.jsonrpc.test('this is a string')[u'result'],
      u'this is a string')


if __name__ == '__main__':
  json_serve_thread()