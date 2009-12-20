from inspect import getargspec
from functools import wraps
from jsonrpc.site import jsonrpc_site
from jsonrpc.exceptions import *


def jsonrpc_method(name, authenticated=False, safe=False):
  def decorator(func):
    arg_names = getargspec(func)[0][1:]
    if authenticated:
      if authenticated is True:
        arg_names = ['username', 'password'] + arg_names # TODO: this is an assumption
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
              user = authenticate(username=kwargs['username'], password=kwargs['password'])
              if user is not None:
                kwargs.pop('username')
                kwargs.pop('password')
            else:
              raise InvalidParamsError('Authenticated methods require at least '
                                       '[username, password] or {username: password:} arguments')
          if user is None:
            raise InvalidCredentialsError
          request.user = user
          return func(request, *args, **kwargs)
        return func(request, *args, **kwargs)
    else:
      _func = func
    _func.json_args = arg_names
    _func.json_arg_types = ['any'] * len(arg_names)
    _func.json_return_type = 'any'
    _func.json_method = name
    _func.json_safe = safe
    jsonrpc_site.register(name, _func)
    return _func
  return decorator
