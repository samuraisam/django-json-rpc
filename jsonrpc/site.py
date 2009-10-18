from types import NoneType
from django.http import HttpResponse
from jsonrpc.exceptions import *

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
    encode_kw = lambda p: dict([(str(k), v) for k, v in p.iteritems()])
    apply_version = {'2.0': lambda f, r, p: f(r, **encode_kw(p)) if type(p) is dict else f(r, *p),
                     '1.0': lambda f, r, p: f(r, *p)}
    apply = apply_version['1.0']
    try:
      if not request.method.lower() == 'post':
        raise RequestPostError
      try:
        D = json.loads(request.raw_post_data)
      except:
        raise InvalidRequestError
      if 'method' not in D or 'params' not in D:
        raise InvalidParamsError('Request requires str:"method" and list:"params"')
      if D['method'] not in self.urls:
        raise MethodNotFoundError('Method not found. Available methods: %s' % (
                        '\n'.join(self.urls.keys())))
      
      if 'jsonrpc' in D:
        if str(D['jsonrpc']) not in apply_version:
          raise InvalidRequestError('JSON-RPC version %s not supported.' % D['jsonrpc'])
        apply = apply_version[D['jsonrpc']]
        request.jsonrpc_version = str(D['jsonrpc'])
      else:
        request.jsonrpc_version = '1.0'
      
      R = apply(self.urls[str(D['method'])], request, D['params'])
      
      assert sum(map(lambda e: isinstance(R, e), 
        (dict, str, unicode, int, long, list, set, NoneType, bool))), \
        "Return type not supported"
      
      response['result'] = R
      response['id'] = D['id'] if 'id' in D else None
      
      status = 200
      
    except KeyboardInterrupt:
      raise
    except Error, e:
      response['error'] = e.json_rpc_format
      status = e.status    
    except Exception, e:
      # exception missed by others
      other_error = OtherError(e)
      response['error'] = other_error.json_rpc_format
      status = other_error.status    
      
    from django.core.serializers.json import DjangoJSONEncoder
    
    try:
        # in case we do something json doesn't like, we always get back valid json-rpc response
        json_rpc = json.dumps(response,cls=DjangoJSONEncoder)
    except Exception, e:
      # exception missed by others
      other_error = OtherError(e)
      response['result'] = None
      response['error'] = other_error.json_rpc_format
      status = other_error.status    
      
      json_rpc = json.dumps(response,cls=DjangoJSONEncoder)
      
    
    return HttpResponse(json_rpc, status=status,content_type='application/json-rpc')


jsonrpc_site = JSONRPCSite()
