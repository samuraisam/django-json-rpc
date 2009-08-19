from functools import wraps
from jsonrpc.site import jsonrpc_site
from jsonrpc.exceptions import *


def jsonrpc_method(name, authenticated=False):
  def decorator(func):
    func.json_method = name
    if authenticated:
      from django.contrib.auth import authenticate
      @wraps(func)
      def _func(request, *args, **kwargs):
        try:
          creds = args[:2]
          user = authenticate(username=args[0],password=args[1])
          if user is None:
            raise InvalidCredentialsError
        except IndexError:
          raise InvalidParamsError('Authenticated methods require at least [username, password] arguments')
        else:
          request.user = user
          return func(request, *args[2:], **kwargs)
    else:
      _func = func
    jsonrpc_site.register(name, _func)
    return _func
  return decorator