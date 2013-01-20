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
# Last mod  : 27-Sep-2006
# -----------------------------------------------------------------------------

import re, mimetypes, urllib, zlib

__doc__ = """\
This modules defines an abstract class for HTTP clients, that creates a simple,
easy to understand, low-level wrapper for existing HTTP implementation. It
expects to have simple datatypes as input for building the request, and expects
to have the response a string.

The HTTPClient class has a fast response parser that is able to update
important information withing the client.

HTTPClient subclasses are instanciated and bound to every session. As HTTPClient
are stateful (they aggregate session state), they are not meant to be shared
among different sessions.
"""

# TODO: Find more use cases for chunked mode
# TODO: Add cookie encode/decode functions

FILE_ATTACHMENT    = 0
CONTENT_ATTACHMENT = 1

RE_CONTENT_LENGTH  = re.compile("^\s*Content-Length\s*:\s*([0-9]+)", re.I|re.MULTILINE)
RE_CONTENT_ENCODING= re.compile("^\s*Content-Encoding\s*:(.*)\r\n", re.I|re.MULTILINE)
RE_CONTENT_TYPE    = re.compile("^\s*Content-Type\s*:(.*)\r\n",   re.I|re.MULTILINE)
RE_CHARSET         = re.compile("\s*charset=([\w\d_-]+)",           re.I|re.MULTILINE)
RE_LOCATION        = re.compile("^\s*Location\s*:(.*)\r\n",          re.I|re.MULTILINE)
RE_SET_COOKIE      = re.compile("^\s*Set-Cookie\s*:(.*)\r\n",        re.I|re.MULTILINE)
RE_CHUNKED         = re.compile("^\s*Transfer-Encoding\s*:\s*chunked\s*\r\n", re.I|re.MULTILINE)
CRLF               = "\r\n"
BOUNDARY           = '----------fbb6cc131b52e5a980ac702bedde498032a88158$'
DEFAULT_MIMETYPE   = 'text/plain'
DEFAULT_ATTACH_MIMETYPE = 'application/octet-stream'

# NOTE: A useful reference for understanding HTTP is the following website
# <http://www.jmarshall.com/easy/http>
class HTTPClient:
	"""Abstract class for an 'HTTPClient'. As explained in the module
	documentation, the 'HTTPClient' is a an object-oriented interface to
	low-level HTTP communication infrastructure. The 'HTTPClient' is stateful,
	in the sense that it aggregates the status resulting from requests and
	responses."""

	def __init__( self, encoding="latin-1" ):
		"""Creates a new HTTPClient with the given 'encoding' as default
		encofing ('latin-1' is the default)."""
		self._method     = "GET"
		self._url        = None
		self._host       = None
		self._protocol   = None
		self._status     = None
		self._redirect   = None
		self._newCookies = None
		self._responses  = None
		self._onLog      = None
		self._cache      = None
		self.verbose     = 0
		self.encoding    = encoding
		self.retryDelay  = 0.100
		self.retryCount  = 5

	def _log( self, *args ):
		"""Logs data to stdout or forwards it to self._onLog"""
		if self._onLog:
			self._onLog(*args)
		else:
			print " ".join(map(str,args))

	def setCache( self, cache ):
		"""Set a cache"""
		self._cache = cache
	
	def method( self ):
		"""Returns the method of the last request by this HTTP client."""
		return self._method

	def url( self ):
		"""Returns the last URL processed by this HTTP client."""
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
		if not self._responses:
			return ""
		elif len(self._responses) == 1:
			return self._responses[0][-1]
		else:
			return "".join(r[-1] for r in self._responses)

	def dataSize( self ):
		"""Returns the total size of the responses."""
		total = 0
		for r in self._responses:
			total += len(r)
		return total

	def info( self, level=1 ):
		return "%s %s (%s)" % (self.method(), self.url(), self.status())
		# return "\n".join((
		# 	"URL           : %s" % (self.url()),
		# 	"- status      : %s" % (self.status()),
		# 	"- redirect    : %s" % (self.redirect()),
		# 	"- cookies(new): %s" % (self.newCookies()),
		# 	"- responses   : #%s (%sbytes)" % (len(self.responses()),self.dataSize()),
		# ))

	def encode( self, fields=(), attach=() ):
		"""Encodes the given fields and attachments (as given to POST) and
		returns the request body and content type for sending the encoded
		data.  This method can be used to bypass Curl own form encoding
		techniques."""
		content = []
		if not fields and not attach: return "", DEFAULT_MIMETYPE
		if fields:
			for name, value in fields:
				content.append("--" + BOUNDARY)
				content.append('Content-Disposition: form-data; name="%s"' % name)
				content.append('')
				content.append(self._valueToString(value))
		if attach:
			attach = self._ensureAttachment(attach)
			for name, filename, atype in attach:
				content.append("--" + BOUNDARY)
				if atype == FILE_ATTACHMENT:
					f     = file(filename, 'r')
					value = f.read()
					f.close()
					mime_type = mimetypes.guess_type(filename)[0] or DEFAULT_ATTACH_MIMETYPE
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

	def GET( self, url, headers=None ):
		"""Gets the given URL, setting the given headers (as a list of
		strings)."""
		raise Exception("GET method must be implemented by HTTPClient subclasses.")

	def POST( self, url, data=None, mimetype=None, fields=None, attach=None, headers=None ):
		"""Posts the given data (as urlencoded string), or fields as list of
		(name, value) pairs and/or attachments as list of (name, value, type)
		triples. Headers attributes are the same as for the @GET
		method.
		
		The @attach parameter is quite special, as the value will depend on the
		type: if type is @FILE_ATTACHMENT, then value is simply the path to the
		file, but if the type is @CONTENT_ATTACHMENT, the value is expected to
		be a triple (filename, mimetype, value).
		"""
		raise Exception("GET method must be implemented by HTTPClient subclasses.")
	
	def _ensureAttachment( self, attach ):
		"""Ensures that the given attachment is a list of attachments. For
		instance if attach is a single attachment, it will be returned as
		`[attach]`."""
		if attach is None: return attach
		if len(attach) == 3:
			for a in attach:
				if type(a) in (tuple,list) and len(a) == 3:
					continue
				return [attach]
		return attach

	def _valueToString( self, value ):
		"""Ensures that the given value will be an encoded string, encoded in
		this HTTPClient default encoding (set it with the @encoding
		attribute)."""
		if   type(value) == unicode: value = value.encode(self.encoding)
		elif value == None: value = ""
		else: value = str(value)
		return value

	def _valueToPostData( self, value ):
		"""Encodes the given value as an url-encoded string suitable for
		post-data. If the value is a string, it will be left as-s (only
		converted to the default encoding)"""
		if   type(value) == str:
			return value
		elif type(value) == unicode:
			return value
		elif type(value) in (list,tuple):
			return urllib.urlencode(value)
		elif type(value) == dict:
			return urllib.urlencode(value)
		else:
			# It should be a Pair... but we cannot check it because of circular
			# imports
			return value.asURL()

	def _absoluteURL( self, url ):
		"""Returns the absolute URL for the given url"""
		if self.host() == None or url == None or url.find("://") != -1:
			res = url
		elif url[0] == "/":
			res = "%s://%s%s" % (self.protocol(), self.host(), url)
		else:
			res = "%s://%s/%s" % (self.protocol(), self.host(), url)
		return str(res)

	def _parseResponse( self, message):
		"""Parse the message, and return a list of responses and headers. This
		might occur when there is a provisional response in between, or when
		location are followed. The result is a list of (firstline, headers,
		body), all as unparsed stings."""
		res     = []
		off     = 0
		self._newCookies = []
		# FIXME: I don't get why we need to iterate here
		# (it's probably when you have multiple responses)
		while off < len(message):
			body = ""
			eol  = message.find(CRLF, off)
			eoh  = message.find(CRLF + CRLF, off)
			if eol == -1: break
			if eoh == -1: eoh = len(message)
			first_line       = message[off:eol]
			headers          = message[eol+2:eoh]
			# FIXME: This is not very efficient, we should parse all headers
			# into a structure, rahter than searching
			charset          = RE_CHARSET.search(headers)
			is_chunked       = RE_CHUNKED.search(headers)
			content_length   = RE_CONTENT_LENGTH.search(headers)
			content_encoding = RE_CONTENT_ENCODING.search(headers)
			content_type     = RE_CONTENT_TYPE.search(headers)
			if content_encoding:
				content_encoding = content_encoding.group(1)
			if content_type:
				content_type     = content_type.group(1)
			if charset:
				encoding   = charset.group(1)
			else:
				encoding   = self.encoding
			# If there is a content-length specified, we use it
			if content_length:
				content_length = int(content_length.group(1))
				off        = eoh + 4 + content_length
				body       = self._decodeBody(message[eoh+4:off], content_encoding, encoding)
			# Otherwise, the transfer type may be chunks
			elif is_chunked:
				# FIXME: For the moment, chunks are supposed to be separated by
				# CRLF + CRLF only (this is what google.com returns)
				off        = message.find(CRLF + CRLF, eoh + 4)
				if off == -1: off = len(message) 
				body       = self._decodeBody(message[eoh+4:off], content_encoding, encoding)
			# Otherwise the body is simply what's left after the headers
			else:
				if len(message) > eoh+4:
					body = self._decodeBody(message[eoh+4:], content_encoding, encoding)
				off = len(message)
			location, cookies = self._parseStatefulHeaders(headers)
			# WTF: 
			self._redirect    = location
			self._newCookies.extend(self._parseCookies(cookies))
			# FIXME: I don't know if it works properly, but at least it handles
			# responses from <http://www.contactor.se/~dast/postit.cgi> properly.
			if first_line and first_line.startswith("HTTP"):
				res.append([first_line, headers, body])
			# If the first line does not start with HTTP, then this may be
			# the rest of the body from a previous response
			else:
				assert res, "There must be a first line"
				res[-1][-1] = res[-1][-1] + CRLF + CRLF + first_line
				if headers: res[-1][-1] = res[-1][-1] + headers
				if body: res[-1][-1] = res[-1][-1] + body 
		# TODO: It would be good to communicate headers and first_line back
		self._responses = res
		return res

	def _decodeBody( self, body, contentEncoding=None, encoding=None ):
		if contentEncoding:
			if contentEncoding.lower().strip() == "gzip":
				body = zlib.decompress(body)
				#if encoding: return body.decode(encoding)
				#else: return body
				return body
			else:
				raise Exception("Unsupported content encoding: " + contentEncoding)
		else:
			# FIXME: Should not force encoding, only if it's a string
			#if encoding: return body.decode(encoding)
			return body

	def _parseStatefulHeaders( self, headers ):
		"""Return the Location and Set-Cookie headers from the given header
		string."""
		# We add an extra carriage, because some regexes will expect a carriage
		# return at the end
		headers += "\r\n"
		location    = RE_LOCATION.search(headers)
		if location: location = location.group(1).strip()
		cookies    = RE_SET_COOKIE.findall(headers)
		set_cookie = ";".join(cookies)
		return location, set_cookie
	
	def _parseCookies( self, cookies ):
		"""Returns a pair (name, value) for the given cookies, given as text."""
		_cookies   = {}
		res        = []
		if not cookies: return res
		for cookie in cookies.split(";"):
			equal = cookie.find("=")
			if equal > 0:
				key           = cookie[:equal].strip()
				value         = cookie[equal+1:].strip()
				_cookies[key] = value
		for key, value in _cookies.items():
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

# EOF - vim: tw=80 ts=4 sw=4 noet
