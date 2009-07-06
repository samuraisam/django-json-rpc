from functools import wraps
from jsonrpc.site import jsonrpc_site

def jsonrpc_method(name, authenticated=False):
  def decorator(func):
    func.json_method = name
    if authenticated:
      from django.contrib.auth.models import User, check_password
      @wraps(func)
      def _func(request, *args, **kwargs):
        try:
          creds = args[:2]
          user = User.objects.get(username=args[0])
          if not check_password(args[1], user.password):
            raise Exception('JSON-RPC: invalid login credentials')
        except IndexError:
          raise Exception('JSON-RPC: authenticated methods require '
                          'at least [username, password] arguments')
        except User.DoesNotExist:
          raise Exception('JSON-RPC: username not found')
        else:
          request.user = user
          return func(request, *args[2:], **kwargs)
    else:
      _func = func
    jsonrpc_site.register(name, _func)
    return _func
  return decorator