#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : WWWClient - Python client Web toolkit
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre <sebastien@xprima.com>
# Creation  : 19-Jun-2006
# Last mod  : 19-Jun-2006
# -----------------------------------------------------------------------------

import urllib, urllib2, httplib, mimetypes
import urlparse
import re

__version__ = "2.0"

HTTP    = httplib.HTTPConnection
HTTPS   = httplib.HTTPSConnection

GET     = "GET"
POST    = "POST"
HEAD    = "HEAD"
METHODS = (GET, POST, HEAD)

DEFAULT_MIME = "text/plain"

RE_HEADER = re.compile(r"(.*?):\s*(.*?)\s*$")
RE_COOKIE = re.compile(r"(.*);?")

# -----------------------------------------------------------------------------
#
# PARAMETERS
#
# -----------------------------------------------------------------------------

class Parameters:
	"""Parameters are list of pairs (name,values) quite similar to
	dictionaries, excepted that there can be multiple values for a single key,
	and that the order of the keys is preserved."""

	def __init__( self, params=None ):
		self.pairs = []
		self.merge(params)

	def set( self, name, value=None ):
		"""Sets the given name to hold the given value. Every previous value set
		or added to the given name will be cleared."""
		self.clear(name)
		self.add(name, value)
	
	def add( self, name, value=None ):
		"""Adds the given value to the given name. This does not destroy what
		already existed."""
		self.pairs.append((name, value))
	
	def clear( self, name ):
		"""Clears all the (name,values) pairs which have the given name."""
		self.pairs = filter(lambda x:x[0]!= name, self.pairs)

	def merge( self, parameters ):
		"""Merges the given parameters into this parameters list."""
		if parameters == None: return
		if type(parameters) == dict:
			for name, value in parameters.items():
				self.add(name, value)
		elif type(parameters) in (tuple, list):
			for name, value in parameters:
				self.add(name, value)
		else:
			for name, value in parameters.pairs:
				self.add(name, value)

	def encode( self ):
		"""Returns an URL-encoded version of this parameters list."""
		return urllib.urlencode(self.pairs)
	
	def __repr__(self):
		return repr(self.pairs)

# -----------------------------------------------------------------------------
#
# HTTP REQUEST WRAPPER
#
# -----------------------------------------------------------------------------

class Request:
	"""The Request object encapsulates an HTTP request so that it is easy to
	specify headers, cookies, data and attachments."""

	BOUNDARY = "---------------------------7d418b1ee20fc0"
	
	def __init__( self, method=GET, url="/", params=None ):
		self._url        = url
		self._method     = method.upper()
		self._data       = None
		self._dataType   = DEFAULT_MIME
		self._headers    = {}
		self.params      = Parameters(params)
		self.cookies     = Parameters()
		self.attachments = []
		# Ensures that the method is a proper one
		if self._method not in METHODS:
			raise Exception("Method not supported: %s" % (method))
	
	def attach( self, name, path=None, data=None, mime=None ):
		"""Attach the given file or data. Mime type should be given."""
		if path != None:
			if not mime:
				mime = mimetypes.guess_type(path)[0]
			fd   = open( path, 'rb' )
			data = fd.read()
			fd.close()
		else:
			path = name
		if not mime: mime = DEFAULT_MIME
		self.attachments.append((name, mime, path, data))
	
	def data( self, data=None, mime=None ):
		"""If no parameters are given, returns the data and its MIME type, if
		parameters are given, sets either data and/or MIME type."""
		if data == mime == None:
			return (self._data, self._dataType)
		if data != None:
			self._data = data
		if mime != None:
			self._dataType = mime

	def method( self ):
		"""Returns the method for this request"""
		return self._method

	def url( self ):
		"""Returns this request url"""
		if self.params.pairs:
			if self._method == POST and not self._data:
				return self._url
			else:
				return self._url + "?" + self.params.encode()
		else:
			return self._url
	
	def header( self, name, value=urllib2 ):
		"""Gets or set the given header."""
		if value == urllib2:
			return self._headers.get(name)
		else:
			self._headers[name] = str(value)

	def headers( self ):
		"""Returns the headers for this request, sorted in the proper order."""
		headers = {}
		headers.update(self._headers)
		# Takes care of cookies
		if self.cookies.pairs:
			headers.setdefault('Cookie', ";".join([ "%s=%s" % (k,urllib.quote(v)) for k,v in self.cookies.pairs]))
		# Takes care of content type
		if self.attachments:
			headers.setdefault("Content-Type", "multipart/form-data; boundary=%s" % (Request.BOUNDARY))
		elif self._method == POST:
			headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
		# Takes care of content length
		body = str(self.body())
		if body or headers.get("Content-Type"):
			headers.setdefault("Content-Length", str(len(body)))
		return headers
	
	def body( self ):
		"""Returns this request body, including attachments."""
		body = ""
		if self.attachments:
			body += '--%s\r\n' % (Request.BOUNDARY)
			# We add the data, if any
			if self._data:
				body += 'Content-Disposition: form-data"%s"\r\n'
				body += 'Content-Type: %s\r\n\r\n' % (self._dataType)
				body += self._data
				body += '--%s\r\n' % (Request.BOUNDARY)
			# And 
			for name, path, mime, data in self.attachments:
				if path:
					body += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n'%(name, path)
				else:
					body += 'Content-Disposition: form-data; name="%s"\r\n' % (name)
				body += 'Content-Transfer-Encoding: binary\r\n'
				body += 'Content-Type: %s\r\n\r\n' % (mime)
				body += str(data) + '\r\n'
				body += '--%s\r\n' % (Request.BOUNDARY)
		elif self._data:
			body = self._data
		if self._method == POST:
			return self.params.encode()
		else:
			return body

# -----------------------------------------------------------------------------
#
# TRANSACTION
#
# -----------------------------------------------------------------------------

class Transaction:
	"""A transaction encaspulates a request and its responses.
	
	Attributes::

		@session			Enclosing session
		@request			Initiating request
		@response			Response to the request (None by default)
		@data				Response data
		@cookies			Response cookies
		@redirect			Transaction for the redirection (None by default)
		@done				Tells if the transaction was executed or not
	
	"""

	def __init__( self, session, request ):
		self.session  = session
		self.request  = request
		self.response = None 
		self.data     = None
		self.cookies  = Parameters()
		self.status   = None
		self.redirect = None
		self.done     = False
	
	def do( self, mergeCookies=True ):
		if self.done: return
		# OLD HTTPLIB
		# ==================================
		# We prepare the headers
		headers = self.request.headers() 
		headers["Connection"] = "close"
		# We send the request
		connection = self.session.protocol(self.session.host)
		connection.request(self.request.method(), self.request.url(),
		self.request.body(), headers )
		print self.request.method(), self.request.url()
		# And get the response
		self.response = connection.getresponse()
		self.status   = self.response.status
		try:
			self.data  = self.response.read()
		except httplib.IncompleteRead, e:
			raise e
		print "REQ", self.request.url()
		print "REQ", self.request.headers()
		print "REQ", self.request.body()
		print "REPONSE", self.status
		print "REPONSE", self.response.msg
		# ==================================
		
		# full_url = self.session._absoluteURL(self.request.url())
		# print "Doing", self
		# request = urllib2.Request( full_url, self.request.body(), self.request.headers())
		# print "REQ ",  full_url
		# self.response = urllib2.urlopen(request)
		# self.data     = self.response.read()
		# print "RES ", self.response.url
		# print "DATA", len(self.data)
# 
		redirect_url = None
		# We parse the response headers (for cookies)
		for header in self.response.msg.headers:
			match = RE_HEADER.match(header)
			if not match: continue
			header, value = match.group(1), match.group(2)
			if header.lower().strip() == "set-cookie":
				name, cookie_value = RE_COOKIE.match(value).group(1).split("=", 1)
				self.cookies.add(name, urllib.unquote(cookie_value))
			elif header.lower().strip() == "location":
				redirect_url = value

		print "REDIRECT", redirect_url
		print
		# We merge the cookies if necessary
		if mergeCookies:
			self.session.cookies.merge(self.cookies)

		# We take care of URL redirection
		#if redirect_url != None:
		#	self.redirect = self.session.get(redirect_url, do=False)
		self.done = True
		return self

# -----------------------------------------------------------------------------
#
# SESSION
#
# -----------------------------------------------------------------------------

class SessionException(Exception): pass
class Session:
	"""A Session encapsulates a number of transactions (couples of request and
	responses). The session stores common state (the cookies), that is shared by
	the different transactions. Each session has a maximum number of transaction
	which is given by its @maxTransactions attribute.

	Attributes::

		@host				Session host (by name or IP)
		@protocol			Session protocol (either HTTP or HTTPS)
		@transactions		List of transactions
		@maxTransactions	Maximum number of transactions in registered in
							this session
		@cookies			List of cookies for this session
		@userAgent			String for this user session agent

	"""

	MAX_TRANSACTIONS = 10

	def __init__( self, url=None ):
		"""Creates a new session at the given host, and for the given
		protocol."""
		self.host            = None
		self.protocol        = HTTP
		self.transactions    = []
		self.cookies         = Parameters()
		self.userAgent       = "Mozilla/5.0 (X11; U; Linux i686; fr; rv:1.8.0.4) Gecko/20060608 Ubuntu/dapper-security"
		self.maxTransactions = self.MAX_TRANSACTIONS
		if url: self.get(url)

	def last( self ):
		"""Returns the last transaction of the session, or None if there is not
		transaction in the session."""
		if not self.transactions: return None
		return self.transactions[-1]
	
	def referer( self ):
		last = self.last()
		if not last: return None
		if self.protocol == HTTP: protocol = "http://"
		elif self.protocol == HTTPS: protocol = "https://"
		else: raise Exception("Incomplete implementation")
		url = protocol + self.host + last.request.url()
		return url

	def _createRequest( self, **kwargs ):
		request = Request(**kwargs)
		last    = self.last()
		#request.header("User-Agent", self.userAgent)
		request.header("Accept", "text/html; */*")
		request.header("Connection", "close")
		if last: request.header("Referer", self.referer())
		if self.host: request.header("Host", self.host)
		return request

	def get( self, url="/", params=None, follow=True, do=True ):
		print "GETTING", url
		url = self.__processURL(url)
		request = self._createRequest( url=url, params=params )
		transaction = Transaction( self, request )
		self.__addTransaction(transaction)
		# We do the transaction
		if do:
			transaction.do()
			# And follow the redirect if any
			#while transaction.redirect and follow:
			#	transaction = transaction.redirect.do()
		return transaction

	def post( self, url=None, params=None, do=True ):
		url = self.__processURL(url)
		request = self._createRequest( method=POST, url=url, params=params )
		request.cookies.add("RMID", "cf609f024496e240")
		request.header("Connection", "close")
		transaction = Transaction( self, request )
		self.__addTransaction(transaction)
		if do: transaction.do()
		return transaction
	
	def submit( self, form, values=None, action=None,  method=POST, do=True ):
		"""Submits the given form with the current values and action (first
		action by default) to the form action url, and doing
		a POST or GET with the resulting values (POST by default).

		The submit method is a convenience wrapper that processes the given form
		and gives its values as parameters to the post method."""
		# We fill the form values
		if values: form.fill(**values)
		# We set the form action
		if action != None: 
			# FIXME: Checks that there are corresponding actions
			action = filter(lambda a:a.get("name") == action, form.actions())[0]
			form.values[action.get("name")] = action.get("value")
		# And we submit the form
		url = form.action
		if method == POST:
			return self.post( url, params=form.parameters(), do=do )
		elif method == GET:
			return self.get( url, params=form.parameters(), do=do )
		else:
			raise SessionException("Unsupported method for submit: " + method)

	def _absoluteURL( self, url ):
		"""Returns the absolute URL for the given URL, using this session host
		and protocol."""
		if url.startswith("http") and url.find("//") != -1:
			return url
		elif url and url[0] == "/":
			return  self.protocol + "://" + self.host + url
		else: 
			return  self.protocol + "://" + self.host + "/" + url

	def __addTransaction( self, transaction ):
		"""Adds a transaction to this session."""
		if len(self.transactions) > self.maxTransactions:
			self.transactions = self.transactions[1:]
		self.transactions.append(transaction)
	
	def __processURL( self, url ):
		if url == None and not self.transactions: url = "/"
		if url == None and self.transactions: url = self.last().request.url()
		# If we have no default host, then we ensure that there is an http
		# prefix (for instance, www.google.com could be mistakenly interpreted
		# as a path)
		if self.host == None and not url.startswith("http"): url = "http://" + url
		# And now we parse the url and update the session attributes
		protocol, host, path, parameters, query, fragment =  urlparse.urlparse(url)
		if   protocol == "http": self.protocol  = HTTP
		elif protocol == "https": self.protocol = HTTPS
		if host: self.host = host
		if path:       url = path
		else:          url = "/"
		if parameters: url += ";" + parameters
		if query:      url += "?" + query
		if fragment:   url += "#" + fragment
		return url

# Events
# - Redirect
# - New cookie
# - Success
# - Error
# - Timeout
# - Exception

# -----------------------------------------------------------------------------
#
# TESTING
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	import scrape
	scraper = scrape.Scraper()

	session = Session("ppg.hebdo.net")
	session.get("login.aspx?msg=")
	login_form = scraper.forms(session.last().data).values()[0].fields()
	login_form.submit(session, frmUserName="gildo", frmPassword="gioia")


	if False:
		# ===
		session = Session("xis.xprima.com")
		session.get("login.spy")
		login_form = scraper.forms(session.last().data)["loginform"]
		login_form.fill( cmd="login", un="sebastien", pw="hell0World")
		session.post(params=login_form.values).do()
		print session.last().redirect
		print session.cookies

# EOF
