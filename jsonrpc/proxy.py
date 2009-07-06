import urllib
from json import dumps, loads
        
class ServiceProxy(object):
  def __init__(self, service_url, service_name=None):
    self.__service_url = service_url
    self.__service_name = service_name

  def __getattr__(self, name):
    if self.__service_name != None:
      name = "%s.%s" % (self.__service_name, name)
    return ServiceProxy(self.__service_url, name)

  def __call__(self, *args):
    return loads(urllib.urlopen(self.__service_url,
                                dumps({
                                  "method": self.__service_name,
                                  'params': args,
                                  'id': 'jsonrpc'})).read())