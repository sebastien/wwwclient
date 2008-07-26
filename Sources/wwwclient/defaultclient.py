#!/usr/bin/env python
# Encoding: iso-8859-1
# -----------------------------------------------------------------------------
# Project   : WWWClient
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# -----------------------------------------------------------------------------
# License   : GNU Lesser General Public License
# Credits   : Xprima.com
# -----------------------------------------------------------------------------
# Creation  : 04-Jun-2006
# Last mod  : 04-Jul-2006
# -----------------------------------------------------------------------------

import httplib, urlparse, client

# TODO: Add retry support
class HTTPClient(client.HTTPClient):
	"""Sends and manages HTTP requests using the 'httplib' and 'urlparse'
	modules. Using the 'curlclient' may be more efficient than using this one."""

	def __init__( self, encoding="latin-1" ):
		client.HTTPClient.__init__(self, encoding)
		self._http = None

	def GET( self, url, headers=None ):
		"""Gets the given URL, setting the given headers (as a list of
		strings)."""
		# We prepare the request
		if headers == None: headers = ()
		self._prepareRequest(method="GET", url=url, headers=headers)
		# And get the response
		return self._performRequest()

	def POST( self, url, data=None, mimetype=None, fields=None, attach=None, headers=None ):
		# If there is already data given, we check that there is no fields or
		# attachments
		if data:
			assert not fields, "Fields must be empty when data is provided"
			assert not attach, "No attachment is allowed when data is provided"
			data = self._valueToPostData(data)
		# Otherwise we encode the data as multipart
		if data == None:
			assert mimetype == None, "Mimetype is ignored when no data is given."
			attach = self._ensureAttachment(attach)
			data, mimetype = self.encode(fields, attach)
		# In case we have a mimetype, we update the list of headers
		# appropriately
		if mimetype:
			if headers == None: headers = []
			headers = list(filter(lambda x: client.RE_CONTENT_TYPE.match(x) == None, headers))
			headers.append("Content-Type: " + mimetype)
		# We add the Content-Length header to the headers list
		headers.append("Content-Length: " + self._valueToString(len(data)))
		# We prepare the request
		self._prepareRequest(method="POST", url=url, headers=headers, body=data)
		# And get the response
		return self._performRequest()

	def _prepareRequest( self, url, headers=(), body=None, method="GET" ):
		assert self._http == None, "Only one request is allowed per instance"
		self._url  = url = self._absoluteURL(url)
		host = self.host()
		if not host: host = urlparse.urlparse(self._url)[1]
		self._http = httplib.HTTPConnection(host)
		http_headers = {}
		for header in headers:
			colon = header.find(":")
			http_headers[header[:colon].strip()] = header[colon+1:]
		request  = self._http.request(method, url, body, http_headers)
		# print "=---------------------------------------"
		# print method, url, host
		# print headers
		# print body
		# print "=---------------------------------------"
		return request

	def _performRequest( self, counter=0 ):
		response = self._http.getresponse()
		if response.version == 10: res = "HTTP/1.0 "
		else: res = "HTTP/1.1 "
		res += str(response.status) + " "
		res += str(response.reason) + client.CRLF
		res += str(response.msg) + client.CRLF
		res += response.read()
		# Copied from perform request
		self._status = response.status
		self._url    = self._url #FIXME: Handle location
		self._protocol, self._host, _, _, _, _ = urlparse.urlparse(self._url)
		self._parseResponse(res)
		if self._http: self._http.close()
		self._http = None
		if self.verbose >= 1: print self.info(), "\n"
		return res

# EOF - vim: tw=80 ts=4 sw=4 noet
