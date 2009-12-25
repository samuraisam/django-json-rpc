import re
from inspect import getargspec
from functools import wraps
from django.utils.datastructures import SortedDict
from jsonrpc.site import jsonrpc_site
from jsonrpc.types import *
from jsonrpc.exceptions import *


KWARG_RE = re.compile(
  r'\s*(?P<arg_name>[a-zA-Z0-9_]+)\s*=\s*(?P<arg_type>[a-zA-Z]+)\s*$')
SIG_RE = re.compile(
  r'\s*(?P<method_name>[a-zA-Z0-9._]+)\s*(\((?P<args_sig>[^)].*)?\)'
  r'\s*(\->\s*(?P<return_sig>.*))?)?\s*$')


def _validate_arg(value, expected):
  if type(value) == expected:
    return True
  return False

def _validate_args(f, *args, **kwargs):
  return

def _eval_arg_type(arg_type, T=Any, arg=None, sig=None):
  try:
    T = eval(arg_type)
  except Exception, e:
    raise ValueError('The type of %s could not be evaluated in %s for %s: %s' %
                    (arg_type, arg, sig, str(e)))
  else:
    if type(T) not in (type, Type):
      raise TypeError('%s is not a valid type in %s for %s' %
                      (repr(T), arg, sig))
    return T

def _parse_sig(sig, arg_names):
  d = SIG_RE.match(sig)
  if not d:
    raise ValueError('Invalid method signature %s' % sig)
  d = d.groupdict()
  ret = [(n, Any) for n in arg_names]
  if 'args_sig' in d and type(d['args_sig']) is str and d['args_sig'].strip():
    for i, arg in enumerate(d['args_sig'].strip().split(',')):
      if '=' in arg:
        if not type(ret) is SortedDict:
          ret = SortedDict(ret)
        dk = KWARG_RE.match(arg)
        if not dk:
          raise ValueError('Could not parse arg type %s in %s' % (arg, sig))
        dk = dk.groupdict()
        if not sum([(k in dk and type(dk[k]) is str and bool(dk[k].strip()))
            for k in ('arg_name', 'arg_type')]):
          raise ValueError('Invalid kwarg value %s in %s' % (arg, sig))
        ret[dk['arg_name']] = _eval_arg_type(dk['arg_type'], None, arg, sig)
      else:
        if type(ret) is SortedDict:
          raise ValueError('Positional arguments must occur '
                           'before keyword arguments in %s' % sig)
        if len(ret) < i + 1:
          ret.append((str(i), _eval_arg_type(arg, None, arg, sig)))
        else:
          ret[i] = (ret[i][0], _eval_arg_type(arg, None, arg, sig))
  if not type(ret) is SortedDict:
    ret = SortedDict(ret)
  return (d['method_name'], 
          ret, 
          (_eval_arg_type(d['return_sig'], Any, 'return', sig)
            if d['return_sig'] else Any))

def _inject_args(sig, types):
  if '(' in sig:
    parts = sig.split('(')
    sig = '%s(%s%s%s' % (
      parts[0], ', '.join(types), 
      (', ' if parts[1].index(')') > 0 else ''), parts[1]
    )
  else:
    sig = '%s(%s)' % (sig, ', '.join(types))
  return sig

def jsonrpc_method(name, authenticated=False, safe=False, validate=False):
  def decorator(func):
    arg_names = getargspec(func)[0][1:]
    X = {'name': name}
    if authenticated:
      if authenticated is True:
        # TODO: this is an assumption
        arg_names = ['username', 'password'] + arg_names 
        X['name'] = _inject_args(X['name'], ('String', 'String'))
        from django.contrib.auth import authenticate
        from django.contrib.auth.models import User
      else:
        authenticate = authenticated
      @wraps(func)  
      def _func(request, *args, **kwargs):
        user = getattr(request, 'user', None)
        is_authenticated = getattr(user, 'is_authenticated', lambda: False)
        if ((user is not None 
              and callable(is_authenticated) and not is_authenticated()) 
            or user is None):
          user = None
          try:
            creds = args[:2]
            user = authenticate(username=creds[0], password=creds[1])
            if user is not None:
              args = args[2:]
          except IndexError: 
            if 'username' in kwargs and 'password' in kwargs:
              user = authenticate(username=kwargs['username'],
                                  password=kwargs['password'])
              if user is not None:
                kwargs.pop('username')
                kwargs.pop('password')
            else:
              raise InvalidParamsError(
                'Authenticated methods require at least '
                '[username, password] or {username: password:} arguments')
          if user is None:
            raise InvalidCredentialsError
          request.user = user
        return func(request, *args, **kwargs)
    else:
      _func = func
    method, arg_types, return_type = _parse_sig(X['name'], arg_names)
    _func.json_args = arg_names
    _func.json_arg_types = arg_types
    _func.json_return_type = return_type
    _func.json_method = method
    _func.json_safe = safe
    _func.json_sig = X['name']
    _func.json_validate = validate
    jsonrpc_site.register(method, _func)
    return _func
  return decorator
