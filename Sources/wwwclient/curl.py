#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : PyCurl Transaction wrapper
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre <sebastien@xprima.com>
# Creation  : 20-Jun-2006
# Last mod  : 04-Jul-2006
# -----------------------------------------------------------------------------

import pycurl, re, time, urlparse, mimetypes, StringIO

# TODO: Find more use cases for chunked mode
# TODO: Add cookie encode/decode functions

__doc__ = """\
The wwwclient.curl module is a wrapper around the PyCurl module that simplifies
writing HTTP clients with curl. This module was designed to be low-level, fast
and easy to use.

It features:

 - Provisional and final responses parsing
 - Cookies support
 - Redirect suport
 - Encoding support for fields
 - File upload support
 - Custom headers support
 - Custom request modification callback
 - Custom form/data encoding function (when there are troubles with Curl)

The basic usage is to instanciate a HTTClient class, and then call GET and POST
methods on the instance. You can decide according to the various attributes what
you want to do (follow redirection, process cookies, etc).

Example:

--
	from curl import HTTPClient
	# Creates the client
	c = HTTPClient()
	# Connects to google.com
	c.GET("http://www.google.com")
	# Follows redirections (if any)
	while c.redirect(): c.GET(t.redirect())
	# And eventually do the search query
	print c.GET("search?hl=en&q=pycurl&btnG=&meta=")
	print c.info()
--

This example is of course very basic, but it gives you the general feel about
how to use it. When looking at the API take care of reading the docstring to
know what kind of value is expected, as headers are expected to be a list of
strings, and attachements are expected to be of a specific format (detailes in
POST).

"""

FILE_ATTACHMENT    = 0
CONTENT_ATTACHMENT = 1

RE_CONTENT_LENGTH  = re.compile("\s*Content-Length\s*:\s*([0-9]+)", re.I|re.MULTILINE)
RE_CONTENT_TYPE    = re.compile("\s*Content-Type\s*:\s*([0-9]+)",   re.I|re.MULTILINE)
RE_CHARSET         = re.compile("\s*charset=([\w\d_-]+)",           re.I|re.MULTILINE)
RE_LOCATION        = re.compile("\s*Location\s*:(.*)\r\n",          re.I|re.MULTILINE)
RE_SET_COOKIE      = re.compile("\s*Set-Cookie\s*:(.*)\r\n",        re.I|re.MULTILINE)
RE_CHUNKED         = re.compile("\s*Transfer-Encoding\s*:\s*chunked\s*\r\n", re.I|re.MULTILINE)
CRLF               = "\r\n"
BOUNDARY           = '----------fbb6cc131b52e5a980ac702bedde498032a88158$'
DEFAULT_MIMETYPE   = 'application/octet-stream'

# NOTE: A useful reference for understanding HTTP is the following website
# <http://www.jmarshall.com/easy/http>
class HTTPClient:
	"""Sends and manages HTTP requests using the PyCURL library. Each instance
	should be used in a single thread (no sharing), because the same Curl
	instance is kept by all methods."""

	def __init__( self, encoding="latin-1" ):
		self._curl       = None
		self._buffer     = None
		self._url        = None
		self._host       = None
		self._protocol   = None
		self._status     = None
		self._redirect   = None
		self._newCookies = None
		self._responses  = None
		self.verbose     = 2
		self.encoding    = encoding
		self.retryDelay  = 0.100
		self.retryCount  = 5

	def url( self ):
		"""Returns the last URL processed by this Curl HTTP interface."""
		return self._url
	
	def host( self ):
		"""Returns the current host"""
		return self._host
	
	def protocol( self ):
		"""Returns the current protocol."""
		return self._protocol

	def status( self ):
		"""Returns the last response status."""
		return self._status
	
	def redirect( self ):
		"""Returns the redirection URL (if any)."""
		if self._redirect == None or self._redirect.find("://") != -1:
			return self._redirect
		if self._redirect[0] == "/":
			return "%s://%s%s" % (self.protocol(), self.host(), self._redirect)
		else:
			return "%s://%s/%s" % (self.protocol(), self.host(), self._redirect)
	
	def newCookies( self ):
		"""Returns the cookies added by the last response."""
		return self._newCookies
	
	def responses( self ):
		"""Returns the list of responses to the last request. The list is
		composed of triples (firstline, headers, body)."""
		return self._responses

	def data( self ):
		"""Returns the last response data."""
		if not self._responses: return None
		else: return self._responses[-1][-1]

	def info( self ):
		return "\n".join((
			"URL          : %s" % (self.url()),
			"Status       : %s" % (self.status()),
			"Redirect     : %s" % (self.redirect()),
			"New-Cookies  : %s" % (self.newCookies()),
			"Responses    : %s" % (len(self.responses())),
		))

	def GET( self, url, headers=None, follow=False ):
		"""Gets the given URL, setting the given headers (as a list of strings),
		and optionnaly following redirects (false by default)."""
		r, s = self._prepareRequest( url, headers )
		self._performRequest()
		if follow and self.redirect(): self.follow()
		return self.data()

	def POST( self, url, data=None, mimetype=None, fields=None, attach=None, headers=None, follow=False ):
		"""Posts the given data (as urlencoded string), or fields as list of
		(name, value) pairs and/or attachments as list of (name, value, type)
		triples. Headers and follow attributes are the same as for the @GET
		method.
		
		The @attach parameter is quite special, as the value will depend on the
		type: if type is @FILE_ATTACHMENT, then value is simply the path to the
		file, but if the type is @CONTENT_ATTACHMENT, the value is expected to
		be a triple (filename, mimetype, value).
		"""
		# If there is no data, we encode it using our custom encoding method
		if data:
			assert not fields, "Fields must be empty when data is provided"
			assert not attach, "No attachment is allowed when data is provided"
		if data == None:
			assert mimetype == None, "Mimetype is ignored when no data is given."
			data, mimetype = self.encodeMultipart(fields, attach)
		# If there is a mimetype specified, we update the fields with the proper
		# content-type
		if mimetype:
			if headers == None: headers = []
			# TODO: Optimize this, it is kind of slow
			headers = list(filter(lambda x: RE_CONTENT_TYPE.match(x) == None, headers))
			headers.append("Content-Type: " + mimetype)
		# We prepare the request
		r, s = self._prepareRequest( url, headers )
		# PyCurl offers three ways to do a POST
		r.setopt(pycurl.POST, 1)
		# If there is data, we attach it
		if data != None: r.setopt(pycurl.POSTFIELDS, data)
		# Now we can perform the request
		self._performRequest()
		if follow and self.redirect(): self.follow()
		return self.data()

	def _valueToString( self, value ):
		"""Ensures that the given value will be an encoded string, encoded in
		this HTTPClient default encoding (set it with the @encoding
		attribute)."""
		if   type(value) == unicode: value = value.encode(self.encoding)
		elif value == None: value = ""
		else: value = str(value)
		return value

	def _absoluteURL( self, url ):
		"""Returns the absolute URL for the given url"""
		if self.host() == None or url == None or url.find("://") != -1:
			res = url
		elif url[0] == "/":
			res = "%s://%s%s" % (self.protocol(), self.host(), url)
		else:
			res = "%s://%s/%s" % (self.protocol(), self.host(), url)
		return str(url)

	def _prepareRequest( self, url, headers = None ):
		"""Returns a pair (request, stringio) corresponding to an HTTP request
		to the given url with the given headers (as a list of strings)"""
		assert self._curl == None, "Only one request is allowed per instance"
		c = self._curl = pycurl.Curl()
		s = self._buffer = StringIO.StringIO()
		c.setopt(c.URL, self._absoluteURL(url))
		c.setopt(pycurl.FOLLOWLOCATION, 0)
		c.setopt(pycurl.HEADER, 1)
		c.setopt(pycurl.WRITEFUNCTION, s.write)
		if headers:
			if type(headers) == tuple: headers = list(headers)
			c.setopt(c.HTTPHEADER, headers)
		return (c, s)

	def _performRequest( self, counter=0 ):
		"""Performs the current HTTP request."""
		r = self._curl
		if self.verbose >= 2: self._curl.setopt(self._curl.VERBOSE, 1)
		try:
			r.perform()
		except:
			if counter == self.retryCount:
				raise e
			else:
				time.sleep(self.retryDelay)
				self._performRequest( counter + 1)
				return
		self._status = r.getinfo(pycurl.HTTP_CODE)
		self._url    = r.getinfo(pycurl.EFFECTIVE_URL)
		self._protocol, self._host, _, _, _, _ = urlparse.urlparse(self._url)
		self._parseResponse()
		self._curl.close()
		self._curl = None
		if self.verbose >= 1: print self.info(), "\n"

	def _parseResponse( self ):
		"""Parse the message, and return a list of responses and headers. This
		might occur when there is a provisional response in between, or when
		location are followed. The result is a list of (firstline, headers,
		body), all as unparsed stings."""
		message = self._buffer.getvalue()
		res     = []
		off     = 0
		self._newCookies = []
		while off < len(message):
			eol = message.find(CRLF, off)
			eoh = message.find(CRLF + CRLF, off)
			if eol == -1: break
			if eoh == -1: eoh = len(message)
			first_line     = message[off:eol]
			headers        = message[eol+2:eoh]
			charset        = RE_CHARSET.search(headers)
			is_chunked     = RE_CHUNKED.search(headers)
			content_length = RE_CONTENT_LENGTH.search(headers)
			if charset:
				encoding   = charset.group(1)
			else:
				encoding   = self.encoding
			# If there is a content-length specified, we use it
			if content_length:
				content_length = int(content_length.group(1))
				off        = eoh + 4 + content_length
				body       = message[eoh+4:off]
			# Otherwise, the transfer type may be chunks
			elif is_chunked:
				# FIXME: For the moment, chunks are supposed to be separated by
				# CRLF + CRLF only (this is what google.com returns)
				off        = message.find(CRLF + CRLF, eoh + 4)
				if off == -1: off = len(message) 
				body       = message[eoh+4:off].decode(encoding)
			# Or there is simply no body
			else:
				off        = eoh + 4
				body       = None
			location, cookies = self._parseStatefulHeaders(headers)
			self._redirect   = location
			self._newCookies.extend(self._parseCookies(cookies))
			# FIXME: I don't know if it works properly, but at # least it handles
			# responses from <http://www.contactor.se/~dast/postit.cgi> properly.
			if first_line:
				# If the first line does not start with HTTP, then this may be
				# the rest of the body from a previous response
				if not first_line.startswith("HTTP"):
					if not res: continue
					res[-1][-1] = res[-1][-1] + CRLF + CRLF + first_line
					if headers: res[-1][-1] = res[-1][-1] + headers
					if body: res[-1][-1] = res[-1][-1] + body 
				# Otherwise we have new response
				else:
					res.append([first_line, headers, body])
		self._responses = res
		return res
	
	def _parseStatefulHeaders( self, headers ):
		"""Return the Location and Set-Cookie headers from the given header
		string."""
		location    = RE_LOCATION.search(headers)
		if location: location = location.group(1).strip()
		set_cookie = RE_SET_COOKIE.search(headers)
		if set_cookie: set_cookie = set_cookie.group(1).strip()
		return location, set_cookie
	
	def _parseCookies( self, cookies ):
		"""Returns a pair (name, value) for the given cookies, given as text."""
		res = []
		if not cookies: return res
		for cookie in cookies.split(";"):
			equal = cookie.find("=")
			key   = cookie[:equal].strip()
			value = cookie[equal+1:].strip()
			res.append((key, value))
		return res

	def _parseHeaders( self, headers ):
		"""Parses all headers and returns a list of (key, value) representing
		them."""
		res = []
		for header in headers.split("\n"):
			colon = header.find(":")
			name  = header[:colon].strip()
			value = header[colon+1:-1]
			if not name: continue
			res.append((name,value))
		return res
	
	def encodeMultipart( self, fields=(), attach=() ):
		"""Encodes the given fields and attachments (as given to POST) and
		returns the request body and content type for sending the encoded
		data.  This method can be used to bypass Curl own form encoding
		techniques."""
		content = []
		for name, value in fields:
			content.append("--" + BOUNDARY)
			content.append('Content-Disposition: form-data; name="%s"' % name)
			content.append('')
			content.append(self._valueToString(value))
		for name, filename, atype in attach:
			content.append("--" + BOUNDARY)
			if atype == FILE_ATTACHMENT:
				f     = file(filename, 'r')
				value = f.read()
				f.close()
				mime_type = mimetypes.guess_type(filename)[0] or DEFAULT_MIMETYPE
			elif atype == CONTENT_ATTACHMENT:
				filename, mime_type, value = filename
			content.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (name, filename))
			content.append('Content-Type: %s' % (mime_type))
			content.append('Content-Transfer-Encoding: binary')
			content.append('')
			content.append(self._valueToString(value))
		content.append('--' + BOUNDARY + '--')
		content.append('')
		body         = CRLF.join(content)
		content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
		return body, content_type

	def encodeMultipartWithCurl(self, fields=(), attach=()):
		"""This is an alternative implementation of the encoder using the Curl
		back-end. This returns nothing, but modifies the current curl request
		so that the fields and attachments are properly registered."""
		# TODO: Handle multiple files
		# TODO: Assert no field override
		field_data = []
		# Takes care of fields
		for name, value in fields:
			value = self._valueToString(value)
			field_data.append((name, (pycurl.FORM_CONTENTS, value)))
		# Takes care of attachments
		for name, value, atype in attach:
			value = self._valueToString(value)
			if atype == FILE_ATTACHMENT:
				field_data.append((name, (pycurl.FORM_FILE, value)))
			elif atype == CONTENT_ATTACHMENT:
				filename, mime_type, value = value
				field_data.append((name, (pycurl.FORM_CONTENTS, value)))
			else:
				raise Exception("Unknown attachment type: %s" % (atype))
		r.setopt(pycurl.HTTPPOST, field_data)
		return None, None

if __name__ == "__main__":
	import os
	# Tests the post
	t = Transaction()
	t.POST('http://www.contactor.se/~dast/postit.cgi',
	attach=[("myfile", os.path.abspath(__file__), FILE_ATTACHMENT)])

# EOF
