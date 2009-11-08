import json
from django.http import HttpResponse
from django.shortcuts import render_to_response
from jsonrpc.site import jsonrpc_site

def browse(request):
  desc = jsonrpc_site.service_desc()
  return render_to_response('browse.html', {
    'methods': desc['procs'],
    'method_names_str': json.dumps(
      [m['name'] for m in desc['procs']])
  })
