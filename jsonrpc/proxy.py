import uuid
from six.moves.urllib import request as urllib_request
from six.moves.urllib import error as urllib_error
from django.test.client import FakePayload

from jsonrpc._json import loads, dumps
from jsonrpc._types import *


class ServiceProxy(object):
    def __init__(self, service_url, service_name=None, version='1.0'):
        self.version = str(version)
        self.service_url = service_url
        self.service_name = service_name

    def __getattr__(self, name):
        if self.service_name != None:
            name = "%s.%s" % (self.service_name, name)
        params = dict(self.__dict__, service_name=name)
        return self.__class__(**params)

    def __repr__(self):
        return "ServiceProxy %r" % {
            'jsonrpc': self.version,
            'method': self.service_name
        }

    def send_payload(self, params):
        """Performs the actual sending action and returns the result"""
        data = dumps({
            'jsonrpc': self.version,
            'method': self.service_name,
            'params': params,
            'id': str(uuid.uuid1())
        }).encode('utf-8')
        headers = {
            'Content-Type': 'application/json-rpc',
            'Accept': 'application/json-rpc',
            'Content-Length': len(data)
        }
        try:
            req = urllib_request.Request(self.service_url, data, headers)
            resp = urllib_request.urlopen(req)
        except IOError as e:
            if isinstance(e, urllib_error.HTTPError):
                if e.code not in (
                        401, 403
                ) and e.headers['Content-Type'] == 'application/json-rpc':
                    return e.read().decode('utf-8')  # we got a jsonrpc-formatted respnose
                raise ServiceProxyException(e.code, e.headers, req)
            else:
                raise e
        return resp.read().decode('utf-8')

    def __call__(self, *args, **kwargs):
        params = kwargs if len(kwargs) else args
        if Any.kind(params) == Object and self.version != '2.0':
            raise Exception('Unsupported arg type for JSON-RPC 1.0 '
                            '(the default version for this client, '
                            'pass version="2.0" to use keyword arguments)')

        r = self.send_payload(params)
        y = loads(r)
        if 'error' in y:
            try:
                from django.conf import settings
                if settings.DEBUG:
                    print('JSONRPC: %s error %r' % (self.service_name, y))
            except:
                pass
        return y


class ServiceProxyException(IOError):
    def __init__(self, code, headers, request):
        self.args = ('An Error Occurred', code, headers, request)
        self.code = code
        self.message = 'An Error Occurred'
        self.headers = headers
        self.request = request


class TestingServiceProxy(ServiceProxy):
    """Service proxy which works inside Django unittests"""

    def __init__(self, client, *args, **kwargs):
        super(TestingServiceProxy, self).__init__(*args, **kwargs)
        self.client = client

    def send_payload(self, params):
        json_data = dumps({
            'jsonrpc': self.version,
            'method': self.service_name,
            'params': params,
            'id': str(uuid.uuid1())
        })
        json_payload = FakePayload(json_data)
        client_args = {
            'wsgi.input': json_payload,
            'CONTENT_LENGTH': len(json_data)
        }
        response = self.client.post(self.service_url, **client_args)
        return response.content.decode('utf-8')
