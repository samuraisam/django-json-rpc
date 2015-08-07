try:
  from django.conf.urls import patterns, url
except ImportError:
  # Compatibility with Django <= 1.3
  from django.conf.urls.defaults import patterns, url

from jsonrpc.site import jsonrpc_site

urlpatterns = patterns('',
  url(r'^json/browse/$', 'jsonrpc.views.browse', name='jsonrpc_browser'),
  url(r'^json/$', jsonrpc_site.dispatch, name='jsonrpc_mountpoint'),
  (r'^json/(?P<method>[a-zA-Z0-9.-_]+)$', jsonrpc_site.dispatch),
)
