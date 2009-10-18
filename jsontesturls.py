from django.conf.urls.defaults import *
from jsonrpc.site import jsonrpc_site

urlpatterns = patterns('', (r'^json/', jsonrpc_site.dispatch))