from django.conf.urls.defaults import *
from jsonrpc.site import jsonrpc_site

urlpatterns = patterns('', 
  (r'^json/$', jsonrpc_site.dispatch),
  (r'^json/(?P<method>[a-zA-Z0-9.]+)$', jsonrpc_site.dispatch)
)