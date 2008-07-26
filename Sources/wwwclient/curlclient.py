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
# Creation  : 20-Jun-2006
# Last mod  : 04-Jul-2006
# -----------------------------------------------------------------------------

import StringIO, urlparse, time, client, pycurl

# TODO: Find more use cases for chunked mode
# TODO: Add cookie encode/decode functions

__doc__ = """\
The 'wwwclient.curl' module is a wrapper around the PyCurl module that simplifies
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
methods on the instance.

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
strings, and attachements are expected to be of a specific format (details in
POST).

"""

# NOTE: A useful reference for understanding HTTP is the following website
# <http://www.jmarshall.com/easy/http>
class HTTPClient(client.HTTPClient):
	"""Sends and manages HTTP requests using the PyCURL library. Each instance
	should be used in a single thread (no sharing), because the same Curl
	instance is kept by all methods."""

	def __init__( self, encoding="latin-1" ):
		client.HTTPClient.__init__(self, encoding)
		self._curl       = None
		self._buffer     = None

	def GET( self, url, headers=None ):
		"""Gets the given URL, setting the given headers (as a list of strings),
		and optionnaly following redirects (false by default)."""
		r, s = self._prepareRequest( url, headers )
		self._performRequest()
		return self.data()

	def POST( self, url, data=None, mimetype=None, fields=None, attach=None,
	headers=None, curlEncode=False ):
		"""Posts the given data (as urlencoded string), or fields as list of
		(name, value) pairs and/or attachments as list of (name, value, type)
		triples. Headers attributes are the same as for the @GET
		method.
		
		The @attach parameter is quite special, as the value will depend on the
		type: if type is @FILE_ATTACHMENT, then value is simply the path to the
		file, but if the type is @CONTENT_ATTACHMENT, the value is expected to
		be a triple (filename, mimetype, value).
		"""
		# If there is data, we expect it to be already encoded
		if data != None:
			assert not fields, "Fields must be empty when data is provided"
			assert not attach, "No attachment is allowed when data is provided"
			if not headers: headers = []
			headers = list(headers)
			if mimetype: headers.append("Content-Type: " + mimetype)
			r, s = self._prepareRequest( url, headers )
			r.setopt(pycurl.POST, 1)
			r.setopt(pycurl.POSTFIELDS, data)
		# If there is no data, we let Curl encode the given fields and
		# attachments
		# TODO: Try to see how to succeed with file given by content using Curl
		elif curlEncode:
			assert mimetype == None, "Mimetype is ignored when no data is given."
			post_data = self.curlEncode(fields, attach)
			r, s = self._prepareRequest( url, headers )
			r.setopt(pycurl.POST, 1)
			r.setopt(pycurl.HTTPPOST, post_data)
		else:
			assert mimetype == None, "Mimetype is ignored when no data is given."
			data, mime_type = self.encode(fields, attach)
			if not headers: headers = []
			headers = list(headers)
			headers.append("Content-Type: " + mime_type)
			r, s = self._prepareRequest( url, headers )
			r.setopt(pycurl.POST, 1)
			r.setopt(pycurl.POSTFIELDS, data)
		# PyCurl offers three ways to do a POST
		# If there is data, we attach it
		# Now we can perform the request
		self._performRequest()
		return self.data()
	
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
		r.perform()
		try:
			#r.perform()
			pass
		except Exception, e:
			if counter == self.retryCount:
				raise e
			else:
				time.sleep(self.retryDelay)
				self._performRequest( counter + 1)
				return
		self._status = r.getinfo(pycurl.HTTP_CODE)
		self._url    = r.getinfo(pycurl.EFFECTIVE_URL)
		self._protocol, self._host, _, _, _, _ = urlparse.urlparse(self._url)
		self._parseResponse(self._buffer.getvalue())
		self._curl.close()
		self._curl = None
		if self.verbose >= 1: print self.info(), "\n"

	def curlEncode(self, fields=(), attach=()):
		"""This is an alternative implementation of the encoder using the Curl
		back-end. This returns nothing, but modifies the current curl request
		so that the fields and attachments are properly registered."""
		# TODO: Handle multiple files
		# TODO: Assert no field override
		field_data = []
		# Takes care of fields
		if fields:
			for name, value in fields:
				value = self._valueToString(value)
				field_data.append((name, (pycurl.FORM_CONTENTS, value)))
		# Takes care of attachments
		if attach:
			for name, value, atype in attach:
				if atype == client.FILE_ATTACHMENT:
					field_data.append((name, (pycurl.FORM_FILE, value)))
				elif atype == client.CONTENT_ATTACHMENT:
					# FIXME: This does not work !
					filename, mime_type, value = value
					field_data.append((name, (pycurl.FORM_FILE, filename, pycurl.FORM_CONTENTS, value,
					pycurl.FORM_CONTENTTYPE, mime_type)))
				else:
					raise Exception("Unknown attachment type: %s" % (atype))
		return field_data

# EOF - vim: tw=80 ts=4 sw=4 noet
