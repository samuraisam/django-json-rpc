from functools import wraps
from jsonrpc.site import jsonrpc_site
from jsonrpc.exceptions import *


def jsonrpc_method(name, authenticated=False, safe=False):
  def decorator(func):
    if authenticated:
      if authenticated is True:
        from django.contrib.auth import authenticate
      else:
        authenticate = authenticated
      @wraps(func)
      def _func(request, *args, **kwargs):
        user = getattr(request, 'user', None)
        is_authenticated = getattr(user, 'is_authenticated', lambda: False)
        if ((user is not None 
              and not callable(is_authenticated) and is_authenticated()) 
            or user is None):
          user = None
          try:
            creds = args[:2]
            user = authenticate(username=creds[0],password=creds[1])
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
          else:
            if user is None:
              raise InvalidCredentialsError
            request.user = user
          return func(request, *args, **kwargs)
    else:
      _func = func
    _func.json_method = name
    _func.json_safe = safe
    jsonrpc_site.register(name, _func)
    return _func
  return decorator