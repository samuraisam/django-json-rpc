import sys
import traceback
from types import NoneType
from django.http import HttpResponse
try:
  import json
except (ImportError, NameError):
  from django.utils import simplejson as json

class JSONRPCSite(object):
  def __init__(self):
    self.urls = {}
  
  @property
  def root(self):
    return [(r'^json/%s/' % k, v) for k, v in self.urls.iteritems()]
  
  def register(self, name, method):
    self.urls[unicode(name)] = method
  
  def dispatch(self, request):
    response = {'error': None, 'result': None}
    try:
      if not request.method.lower() == 'post':
        raise Exception('JSON-RPC: requests most be POST')
      try:
        D = json.loads(request.raw_post_data)
      except:
        raise Exception('JSON-RPC: request poorly formed JSON')
      if 'method' not in D or 'params' not in D:
        raise Exception('JSON-RPC: request requires str:"method" and list:"params"')
      if D['method'] not in self.urls:
        raise Exception('JSON-RPC: method not found')
      
      R = self.urls[str(D['method'])](request, *list(D['params']))
      
      assert sum(map(lambda e: isinstance(R, e), 
        (dict, str, unicode, int, long, list, set, NoneType, bool))), \
        "Return type not supported"
      
      response['result'] = R
      
    except KeyboardInterrupt:
      raise
    except Exception, e:
      error = {
        'name': str(e.__class__.__name__), #str(sys.exc_info()[0]),
        'message': str(e),
        'stack': traceback.format_exc(),
        'executable': sys.executable}
      response['error'] = error
      
    return HttpResponse(json.dumps(response), content_type='application/javascript')


jsonrpc_site = JSONRPCSite()

def jsonrpc_method(name):
  def decorator(func):
    func.json_method = name
    jsonrpc_site.register(name, func)
    return func
  return decorator