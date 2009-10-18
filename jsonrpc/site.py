from types import NoneType
from django.http import HttpResponse
from jsonrpc.exceptions import *

try:
  import json
except (ImportError, NameError):
  from django.utils import simplejson as json


encode_kw = lambda p: dict([(str(k), v) for k, v in p.iteritems()])

def encode_kw11(p):
  if not type(p) is dict:
    return {}
  ret = p.copy()
  removes = []
  for k, v in ret.iteritems():
    try:
      int(k)
    except ValueError:
      pass
    else:
      removes.append(k)
  for k in removes:
    ret.pop(k)
  return ret

def encode_arg11(p):
  if type(p) is list:
    return p
  elif not type(p) is dict:
    return []
  else:
    pos = []
    d = encode_kw(p)
    for k, v in d.iteritems():
      try:
        pos.append(int(k))
      except ValueError:
        pass
    pos = list(set(pos))
    pos.sort()
    return [d[str(i)] for i in pos]


class JSONRPCSite(object):
  def __init__(self):
    self.urls = {}
  
  @property
  def root(self):
    return [(r'^json/%s/' % k, v) for k, v in self.urls.iteritems()]
  
  def register(self, name, method):
    self.urls[unicode(name)] = method
  
  def empty_response(self, version='1.0'):
    resp = {'id': None}
    if version == '1.1':
      resp['version'] = version
      return resp
    if version == '2.0':
      resp['jsonrpc'] = version
    resp.update({'error': None, 'result': None})
    
    return resp
  
  def response_dict(self, request, D, is_batch=False, version_hint='1.0'):
    version = version_hint
    response = self.empty_response(version=version)
    apply_version = {'2.0': lambda f, r, p: f(r, **encode_kw(p)) if type(p) is dict else f(r, *p),
                     '1.1': lambda f, r, p: f(r, *encode_arg11(p), **encode_kw(encode_kw11(p))),
                     '1.0': lambda f, r, p: f(r, *p)}
    
    try:
      if 'method' not in D or 'params' not in D:
        raise InvalidParamsError('Request requires str:"method" and list:"params"')
      if D['method'] not in self.urls:
        raise MethodNotFoundError('Method not found. Available methods: %s' % (
                        '\n'.join(self.urls.keys())))
      
      if 'jsonrpc' in D:
        if str(D['jsonrpc']) not in apply_version:
          raise InvalidRequestError('JSON-RPC version %s not supported.' % D['jsonrpc'])
        version = request.jsonrpc_version = response['jsonrpc'] = str(D['jsonrpc'])
      elif 'version' in D:
        if str(D['version']) not in apply_version:
          raise InvalidRequestError('JSON-RPC version %s not supported.' % D['version'])
        version = request.jsonrpc_version = response['version'] = str(D['version'])
      else:
        request.jsonrpc_version = '1.0'
      
      R = apply_version[version](self.urls[str(D['method'])], request, D['params'])
      
      assert sum(map(lambda e: isinstance(R, e), 
        (dict, str, unicode, int, long, list, set, NoneType, bool))), \
        "Return type not supported"
      
      if 'id' in D and D['id'] is not None: # regular request
        response['result'] = R
        response['id'] = D['id']
        if version == '1.1' and 'error' in response:
          response.pop('error')
      elif is_batch: # notification, not ok in a batch format, but happened anyway
        raise InvalidRequestError
      else: # notification
        return None, 204
      
      status = 200
    
    except Error, e:
      response['error'] = e.json_rpc_format
      if version == '1.1' and 'result' in response:
        response.pop('result')
      status = e.status    
    except Exception, e:
      # exception missed by others
      other_error = OtherError(e)
      response['error'] = other_error.json_rpc_format
      status = other_error.status    
      if version == '1.1' and 'result' in response:
        response.pop('result')
    
    return response, status
  
  def dispatch(self, request):
    if not request.method.lower() == 'post':
      raise RequestPostError
    response = self.empty_response()
    try:
      D = json.loads(request.raw_post_data)
    except:
      raise InvalidRequestError
    if type(D) is list:
      response = [self.response_dict(request, d)[0] for d in D]
      status = 200
    else:
      response, status = self.response_dict(request, D)
      if response is None and not u'id' in D or D[u'id'] is None: # a notification
        return HttpResponse('', status=status)
      
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
      
    
    return HttpResponse(json_rpc, status=status, content_type='application/json-rpc')


jsonrpc_site = JSONRPCSite()
