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
# Creation  : 19-Jun-2006
# Last mod  : 26-Jul-2006
# -----------------------------------------------------------------------------

# TODO: Allow Request to have parameters in body or url and attachments as well
# TODO: Add   sessoin.status, session.headers, session.links(), session.scrape()
# TODO: Add   session.select() to select a form before submit

import urlparse, urllib, mimetypes, re, os, time
import client, defaultclient, scrape

HTTP               = "http"
HTTPS              = "https"
PROTOCOLS          = (HTTP, HTTPS)

GET                = "GET"
POST               = "POST"
HEAD               = "HEAD"
METHODS            = (GET, POST, HEAD)

FILE_ATTACHMENT    = client.FILE_ATTACHMENT
CONTENT_ATTACHMENT = client.CONTENT_ATTACHMENT

# -----------------------------------------------------------------------------
#
# PARAMETERS
#
# -----------------------------------------------------------------------------

class Pairs:
	"""Pairs are list of pairs (name,values) quite similar to
	dictionaries, excepted that there can be multiple values for a single key,
	and that the order of the keys is preserved. They can be easily converted to
	URL parameters, headers and cookies."""

	def __init__( self, params=None ):
		self.pairs = []
		self.merge(params)

	def set( self, name, value=None, replace=False ):
		"""Sets the given name to hold the given value. Every previous value set
		or added to the given name will be cleared."""
		if replace:
			i = 0
			for hname, hvalue in self.pairs:
				if name.lower() == hname.lower(): break
				i += 1
			if i == len(self.pairs):
				self.add(name,value)
			else:
				self.pairs[i] = (name,value)
		else:
			self.add(name, value)
	
	def get( self, name ):
		"""Gets the pair with the given name (case-insensitive)"""
		for key, value in self.pairs:
			if name.lower().strip() == key.lower().strip():
				return value
		return None
	
	def add( self, name, value=None ):
		"""Adds the given value to the given name. This does not destroy what
		already existed."""
		pair = (name,value)
		if pair not in self.pairs: self.pairs.append((name, value))
	
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

	def asURL( self ):
		"""Returns an URL-encoded version of this parameters list."""
		return urllib.urlencode(self.pairs)
	
	def asFormData( self ):
		"""Returns an URL-encoded version of this parameters list."""
		return urllib.urlencode(self.pairs)

	def asHeaders( self ):
		"""Returns a list of header strings."""
		return list("%s: %s" % (k,v) for k,v in self.pairs)

	def asCookies( self ):
		"""Returns these pairs as cookies"""
		return "; ".join("%s=%s" % (k,v) for k,v in self.pairs)
	
	def asFields( self ):
		"""Returns a list of (name, value) couples."""
		return list(self.pairs)

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

	@staticmethod
	def makeAttachment( name, filename=None, content=None,
	mimetype=client.DEFAULT_MIMETYPE ):
		"""Creates an internal representation for an attachment, which is either
		the given filename or the given content, filename and data, as a triple:
		
		>    (<content name>,   <content value>, CONTENT_ATTACHMENT)
		>    (<file name from>, <actual file name>, FILE_ATTACHMENT)
		
		Here 'CONTENT_ATTACHMENT' and 'FILE_ATTACHMENT' are constants from the
		'wwwclient' module to denote the type of attachment.
		"""
		if content != None:
			assert filename, "Filename is required when attaching content"
			assert mimetype, "Mimetype is required when attaching content"
			value = (filename, mimetype, content)
			assert len(value) == 3
			return (name, value, CONTENT_ATTACHMENT)
		elif filename != None:
			assert mimetype == client.DEFAULT_MIMETYPE, "Mimetype is ignored when attaching file"
			return (name, filename, FILE_ATTACHMENT)
		else:
			raise Exception("Expected file or content")

	def __init__( self, method=GET, url =None, host=None, fields=None, attach=(),
	params=None, headers=None, data=None,  mimetype=None ):
		self._method      = method.upper()
		self._url         = url
		self._params      = Pairs(params)
		self._cookies     = Pairs()
		self._headers     = Pairs(headers)
		self._data        = data
		self._fields      = Pairs(fields)
		self._attachments = []
		if attach: self._attachments.extend(attach)
		# Ensures that the method is a proper one
		if self._method not in METHODS:
			raise Exception("Method not supported: %s" % (method))
		if headers:
			for h,v in headers.items():
				self.header(h,v)
		if mimetype:
			self.header("Content-Type", mimetype)

	def method( self ):
		"""Returns the method for this request"""
		return self._method

	def url( self ):
		"""Returns this request url, including the parameters"""
		if self._params.pairs:
			if self._method == POST and self._data != None or self._attachments:
				return self._url
			else:
				return self._url + "?" + self._params.asURL()
		else:
			return self._url

	def params( self ):
		"""Returns the params attached to this request. The params are returned
		as a 'Pair' instance."""
		return self._params
	
	def fields( self ):
		"""Returns the fields of this request, as a 'Pair' instance (if any).
		fields are related to form-submission (see also 'data' method)."""
		return self._fields

	def cookies( self ):
		"""Returns the cookies defined in this request, as a 'Pair' instance (if any)."""
		return self._cookies

	def header( self, name, value=client, replace=False ):
		"""Gets or set the given header."""
		if value == client:
			return self._headers.get(name)
		else:
			self._headers.set(name, str(value), replace=False)

	def headers( self ):
		"""Returns the headers for this request as a Pairs instance."""
		headers = Pairs(self._headers)
		# Takes care of cookies
		if self._cookies.pairs:
			cookie_header = headers.get("Cookie")
			if cookie_header:
				headers.set("Cookie", cookie_header + "; " + self._cookies.asCookies())
			else:
				headers.set("Cookie", self._cookies.asCookies())
		return headers

	def data( self, data=client ):
		"""Sets the urlencoded data for this request. The request will be
		automatically turned into a post."""
		if data == client:
			return self._data
		else:
			assert not self._attachments, "Request already has attachments"
			self._method = POST
			self._data   = data

	def attach( self, name, filename=None, content=None, mimetype=None ):
		"""Attach the given file or content to the request. This will turn the
		request into a post"""
		assert self._data == None, "Request already has data"
		self._method = POST
		self._attachments.append(Request.makeAttachment(name, filename=filename,
		content=content, mimetype=mimetype))

	def attachments( self ):
		"""Returns the list of attachments for this request (as a list of
		triples, as explained in 'makeAttachment')."""
		return self._attachments

# -----------------------------------------------------------------------------
#
# TRANSACTION
#
# -----------------------------------------------------------------------------

class Transaction:
	"""A transaction encaspulates a request and its (zero or more) responses.
	
	Attributes::

	- 'session':  enclosing session
	- 'request':  request
	- 'data':     data
	- 'cookies':  cookies
	- 'redirect': for the redirection (None by default)
	- 'done':     if the transaction was executed or not
	
	"""

	def __init__( self, session, request ):
		self._client     = session._httpClient
		self._session    = session
		self._request    = request
		self._status     = None
		self._cookies    = Pairs()
		self._newCookies = None
		self._done       = False

	def session( self ):
		"""Returns this transaction session"""
		return self._session

	def request( self ):
		"""Returns this transaction request"""
		return self._request

	def status( self ):
		"""Returns the session status"""
		return self._status

	def cookies( self ):
		"""Returns this transaction cookies (including the new cookies, if the
		transaction is set to merge cookies)"""
		return self._cookies
	
	def newCookies( self ):
		"""Returns the list of new cookies."""
		return self._newCookies

	def forms( self, name=None ):
		"""Returns a dictionary with the forms contained in the response. If a
		'name' is given the form with the given name will be returned."""
		assert self._done
		forms = scrape.HTML.forms(self.data())
		if name is None:
			return forms
		else:
			return forms.get(name)

	def links( self ):
		"""Returns a dictionary with the links contained in the response. This
		makes use of the scraping module."""
		assert self._done
		return scrape.HTML.links(self.data())

	def data( self ):
		"""Returns the response data (implies that the transaction was
		previously done)"""
		return self._client.data()

	def redirect( self ):
		"""Returns the URL to which the response redirected, if any."""
		return self._client.redirect()

	def url( self ):
		"""Returns the requested URL."""
		return self.request().url()

	def do( self ):
		"""Executes this transaction. This sends the request to the client which
		actually sends the data to the transport layer."""
		# We do not do a transaction twice
		if self._done: return
		# We prepare the headers
		request  = self.request()
		headers  = request.headers() 
		self._session._log(request.method(), request.url())
		# We merge the session cookies into the request
		request.cookies().merge(self.session().cookies())
		# As well as this transaction cookies
		request.cookies().merge(self.cookies())
		# We send the request as a GET
		if request.method() == GET:
			self._client.GET(
				request.url(),
				headers=request.headers().asHeaders()
			)
		# Or as a POST
		elif request.method() == POST:
			self._client.POST(
				request.url(),
				data=request.data(),
				attach=request.attachments(),
				fields=request.fields().asFields(),
				headers=request.headers().asHeaders()
			)
		# The method may be unsupported
		else:
			raise Exception("Unsupported method:", request.method())
		# We merge the new cookies if necessary
		self._status = self._client.status()
		self._newCookies = Pairs(self._client.newCookies())
		self._done = True
		return self

	def done( self ):
		"""Tells if the transaction is done/complete."""
		return self._done

	def __str__( self ):
		return self.data()

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

	- 'host':            Session host (by name or IP)
	- 'protocol':        Session protocol (either HTTP or HTTPS)
	- 'transactions':    List of transactions
	- 'maxTransactions': Maximum number of transactions in registered in
	                     this session
	- 'cookies':         List of cookies for this session
	- 'userAgent':       String for this user session agent

	"""

	MAX_TRANSACTIONS = 10
	DEFAULT_RETRIES  = 5
	DEFAULT_DELAY    = 1

	def __init__( self, url=None, verbose=True, personality=None, follow=True, do=True ):
		"""Creates a new session at the given host, and for the given
		protocol."""
		self._httpClient      = defaultclient.HTTPClient()
		self._host            = None
		self._protocol        = None
		self._transactions    = []
		self._cookies         = Pairs()
		self._userAgent       = "Mozilla/5.0 (X11; U; Linux i686; fr; rv:1.8.0.4) Gecko/20060608 Ubuntu/dapper-security"
		self._maxTransactions = self.MAX_TRANSACTIONS
		self._referer         = None
		self._verbose         = None
		self._onLog           = None
		self._follow          = follow
		self._do              = do
		self._personality     = personality
		self.MERGE_COOKIES    = True
		self.verbose(verbose)
		if url: self.get(url)

	def verbose( self, status=None ):
		"""Returns the verbose status if no argument is given, ortherwise takes
		a boolean that will define the verbose status."""
		if status is None:
			return self._status
		else:
			self._status = status and 1 or 0
			self._httpClient.verbose = self._status
			return self._status

	def _log( self, *args ):
		"""Logs data to stdout or forwards it to self._onLog"""
		if self._onLog:
			self._onLog(*args)
		else:
			print " ".join(map(str,args))

	def setLogger( self, callback ):
		"""Sets the logger callback (only enabled when the session is set to
		'verbose'"""
		self._onLog = self._httpClient._onLog = callback

	def asFireFox( self ):
		"""Sets this session personality to be FireFox. This returns the
		'FireFox' personaly instance that will be bound to this session, you can
		later change it."""
		return self.setPersonality(FireFox())

	def setPersonality( self, personality ):
		self._personality = personality
		return personality

	def personality( self ):
		"""Returns the personality bound to this session."""
		return self._personality

	def cookies( self ):
		return self._cookies

	def last( self ):
		"""Returns the last transaction of the session, or None if there is not
		transaction in the session."""
		if not self._transactions: return None
		return self._transactions[-1]

	def page( self ):
		"""Returns the data of the last page. This is an alias for
		`self.last().data()`."""
		assert self.last(), "No transaction available."
		return self.last().data()

	def status( self ):
		"""Returns the status of the last transaction. This is an alias for
		`self.last().status()`"""
		assert self.last(), "No transaction available."
		return self.last().status()

	def url( self ):
		"""Returns the URL of the last page. This is an alias for
		`self.last().url()`"""
		assert self.last(), "No transaction available."
		return self.last().url()

	def form( self, name=None ):
		"""Returns the first form declared in the last transaction response data."""
		forms = self.forms(name)
		if not forms: return None
		if name is None: name = forms.keys()[0]
		return forms.get(name)

	def forms( self, name=None ):
		"""Returns a dictionary with the forms contained in the response."""
		assert self.last(), "No transaction available."
		return self.last().forms(name)

	def links( self ):
		"""Returns a list of the links contained in the response."""
		assert self.last(), "No transaction available."
		return self.last().links()

	def attach( self, name, filename=None, content=None, mimetype=client.DEFAULT_MIMETYPE ):
		"""Creates an attachment with the given name for the given `filename` or
		`content` (`mimetype` will be guessed unlesss specified).
		
		This attachment can be used later by giving it as value for the `attach`
		parameter of the `post` method."""
		return Request.makeAttachment( name, filename=filename, content=content,
		mimetype=mimetype)

	def dump( self, path, data=None, overwrite=True ):
		"""Dumps the last retrieved data to the given file."""
		count = 0
		if not overwrite:
			while os.path.exists(path):
				base, ext = os.path.splitext(path)
				i =  base.rfind("-") 
				if i != -1:
					try: v = int(base[i+1:])
					except: v = None
				else:
					v = None
				if v != None: base = base[:i]
				path = base + "-" + str(count) + ext
				count += 1
		f = open(path, "wb")
		data = self.last().data()
		f.write(data)
		f.close()

	def referer( self, value=client ):
		"""Returns/sets the referer for the next request."""
		if value == client:
			if self._referer:
				res = self._referer
				self._referer = None
				return res
			if not self.last(): return None
			else: return self.last().url()
		else:
			self._referer = value

	def get( self, url="/", params=None, headers=None, follow=None, do=None ):
		"""Gets the page at the given URL, with the optional params (as a `Pair`
		instance), with the given headers.

		The `follow` and `do` options tell if redirects should be followed and
		if the request should be sent right away.

		This returns a `Transaction` object, which is `done` if the `do`
		parameter is true."""
		if follow is None: follow = self._follow
		if do is None: do = self._do
		# TODO: Return data instead of session
		url = self.__processURL(url)
		request     = self._createRequest( url=url, params=params, headers=headers )
		transaction = Transaction( self, request )
		self.__addTransaction(transaction)
		# We do the transaction
		if do:
			transaction.do()
			if self.MERGE_COOKIES: self._cookies.merge(transaction.newCookies())
			# And follow the redirect if any
			while transaction.redirect() and follow:
				transaction = self.get(transaction.redirect(), do=True)
		return transaction

	def post( self, url=None, params=None, data=None, mimetype=None,
	fields=None, attach=None, headers=None, follow=None, do=None ):
		"""Posts data to the given URL. The optional `params` (`Pairs`) or `data`
		contain the posted data. The `mimetype` describes the mimetype of the data
		(if it is a special kind of data). The `fields` is a `Pairs` instance of
		values to be encoded within the body. The `attach` may contain some
		attachements created before using the `attach()` method.
		
		You should have a look at the `wwwclient.client` module for more
		information on how the parameters are processed.
		
		As always, this returns a new `Transaction` instance."""
		if follow is None: follow = self._follow
		if do is None: do = self._do
		url = self.__processURL(url)
		if params != None and not isinstance(params, Pairs):
			params = Pairs(params)
		request     = self._createRequest(
			method=POST, url=url, fields=fields, params=params, attach=attach,
			data=data, mimetype=mimetype, headers=headers
		)
		transaction = Transaction( self, request )
		self.__addTransaction(transaction)
		if do:
			transaction.do()
			if self.MERGE_COOKIES: self._cookies.merge(transaction.newCookies())
			# And follow the redirect if any
			while transaction.redirect() and follow:
				transaction = self.get(transaction.redirect(), do=True)
		return transaction

	def submit( self, form, values={}, attach=[], action=None,  method=POST,
	do=None, strip=True ):
		"""Submits the given form with the current values and action (first
		action by default) to the form action url, and doing
		a POST or GET with the resulting values (POST by default).

		The submit method is a convenience wrapper that processes the given form
		and gives its values as parameters to the post method."""
		if do is None: do = self._do
		# We fill the form values
		# And we submit the form
		if type(form) in (unicode, str):
			forms = scrape.HTML.forms(self.last().data())
			if not forms.has_key(form):
				raise SessionException("Form not available: " + form)
			form = forms[form]
		url    = form.action or self.referer()
		fields = form.submit(action=action, strip=strip, **values)
		# FIXME: Manage encodings consistently
		if method == POST or attach:
			return self.post( url, fields=fields, attach=attach, do=do )
		elif method == GET:
			assert not attach, "Attachments are incompatible with GET submission"
			return self.get( url,  params=fields, do=do )
		else:
			raise SessionException("Unsupported method for submit: " + method)

	def ensure(self, expects, action, args=(), kwargs={}, retry=None, delay=None ):
		"""Ensures that the given action (it should be a session instance
		method), executed with the given args complies with the `expect`
		predicate, which will be given his session. You can specify a number of
		retries (maxed to 10), and a delay (in seconds) before each retry.
		
		When finished, this function returns True if it suceeded, or False if
		the retries failed."""
		retry = retry or self.DEFAULT_RETRIES
		if delay == None: delay = self.DEFAULT_DELAY
		res = expects(action(*args,**kwargs))
		while not res and retry:
			res = expects(action(*args,**kwargs))
			time.sleep(delay)
			retry -= 1
		return res

	def __processURL( self, url ):
		"""Processes the given URL, by storing the host and protocol, and
		returning a normalized, absolute URL"""
		old_url = url
		if url == None and not self._transactions: url = "/"
		if url == None and self._transactions: url = self.last().request.url()
		# If we have no default host, then we ensure that there is an http
		# prefix (for instance, www.google.com could be mistakenly interpreted
		# as a path)
		if self._host == None:
			if not url.startswith("http"): url = "http://" + url
		# And now we parse the url and update the session attributes
		protocol, host, path, parameters, query, fragment =  urlparse.urlparse(url)
		if   protocol == "http": self._protocol  = HTTP
		elif protocol == "https": self._protocol = HTTPS
		if host: self._host =  host
		# We recompose the url
		assert not path.startswith("ppg.h")
		url = "%s://%s" % (self._protocol, self._host)
		if   path and path[0] == "/": url += path
		elif path:      url += "/" + path
		else:           url += "/"
		if parameters:  url += ";" + parameters
		if query:       url += "?" + query
		if fragment:    url += "#" + fragment
		return url

	def _createRequest( self, **kwargs ):
		request = Request(**kwargs)
		last    = self.last()
		if self.referer(): request.header("Referer", self.referer())
		if self._personality: self._personality.apply(request)
		return request

	def __addTransaction( self, transaction ):
		"""Adds a transaction to this session."""
		if len(self._transactions) > self._maxTransactions:
			self._transactions = self._transactions[1:]
		self._transactions.append(transaction)

# -----------------------------------------------------------------------------
#
# PERSONALITIES
#
# -----------------------------------------------------------------------------

class Personality:
	"""Personality classes allow to represent the way a specific application
	(typically a browser) interacts with a web server. Some servers do check for
	specific headers and will react differently depending on wether they
	recognize the request as being part of a browser or not.

	Personalities allow to ensure that specific headers are set in all requests,
	so that the requests really look like they come from a specific browser."""

	def __init__( self ):
		pass
	
	def apply( self, request ):
		pass

class FireFox(Personality):
	"""Simulates the way FireFox would behave."""

	def __init__( self ):
		Personality.__init__(self)
		self.desktop        = "X11"
		self.platform       = "Linux i686"
		self.languages      = "en-US"
		self.revision       = "1.9"
		self.geckoVersion   = "2008061015"
		self.firefoxVersion = "3.0"

	def userAgent( self ):
		return "Mozilla/5.0 (%s; U; %s; %s; rv:%s) Gecko/%s Firefox/%s" % (
			self.desktop,
			self.platform,
			self.languages,
			self.revision,
			self.geckoVersion,
			self.firefoxVersion,
		)

	def apply( self, request ):
		request.header( "User-Agent", self.userAgent())
		request.header( "Accept",
		"text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5"
		)
		request.header( "Accept-Language", "en-us,en;q=0.5")
		#request.header( "Accept-Encoding", "gzip,deflate")
		request.header( "Accept-Charset", "ISO-8859-1,utf-8;q=0.7,*;q=0.7")
		request.header( "Keep-Alive", "300")
		request.header( "Connection", "keep-alive")

# Events
# - Redirect
# - New cookie
# - Success
# - Error
# - Timeout
# - Exception

# EOF - vim: tw=80 ts=4 sw=4 noet
