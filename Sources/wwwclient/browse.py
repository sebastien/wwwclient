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
# Last mod  : 26-Sep-2014
# -----------------------------------------------------------------------------

# TODO: Allow Request to have parameters in body or url and attachments as well
# TODO: Add   sessoin.status, session.headers, session.links(), session.scrape()
# TODO: Add   session.select() to select a form before submit

import urlparse, urllib, mimetypes, re, os, sys, time, json, random, hashlib, httplib, base64, socket, tempfile, webbrowser
from   wwwclient import client, defaultclient, scrape, agents

HTTP                = "http"
HTTPS               = "https"
PROTOCOLS           = (HTTP, HTTPS)

GET                 = "GET"
POST                = "POST"
HEAD                = "HEAD"
METHODS             = (GET, POST, HEAD)
DEFAULT_HTTP_CLIENT =  defaultclient.HTTPClient

FILE_ATTACHMENT     = client.FILE_ATTACHMENT
CONTENT_ATTACHMENT  = client.CONTENT_ATTACHMENT

def quote(path):
	return urllib.quote(path, '/%')

def fix(s, charset='utf-8'):
	"""Sometimes you get an URL by a user that just isn't a real
	URL because it contains unsafe characters like ' ' and so on.  This
	function can fix some of the problems in a similar way browsers
	handle data entered by the user:

	>>> url_fix(u'http://de.wikipedia.org/wiki/Elf (Begriffsklärung)')
	'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

	:param charset: The target charset for the URL if the url was
					given as unicode string.
	"""
	if isinstance(s, unicode): s = s.encode(charset, 'ignore')
	scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
	path = urllib.quote(path, '/%')
	qs = urllib.quote_plus(qs, ':&=')
	return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))

def retry( function, times=5, wait=(0.1, 0.5, 1, 1.5, 2), exception=None):
	"""Retries the given function at most `times`, waiting wait seconds. If
	wait is an array, the `wait[0]` will be waited on the first try,
	`wait[1]` on the second, and so on."""
	if times <= 0:
		raise exception
	if type(wait) in (tuple, list):
		delay = wait[0]
		wait  = wait[1:] if len(wait) > 1 else wait
	else:
		delay = wait
	try:
		return function()
	except Exception as e:
		time.sleep(delay)
		return retry(function, times - 1, wait, e)

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

	def has( self, name ):
		"""Tells if the pair has a field with the given name
		(case-insensitive)"""
		for key, value in self.pairs:
			if name.lower().strip() == key.lower().strip():
				return True
		return False

	def add( self, name, value=None ):
		"""Adds the given value to the given name. This does not destroy what
		already existed. (if the pair already exists, it is not added twice."""
		if type(name) == tuple and len(name) == 2:
			if name not in self.pairs: self.pairs.append(name)
		else:
			pair = (name,value)
			if pair not in self.pairs: self.pairs.append((name, value))

	def clear( self, name ):
		"""Clears all the (name,values) pairs which have the given name."""
		self.pairs = filter(lambda x:x[0]!= name, self.pairs)

	def merge( self, parameters ):
		"""Merges the given parameters into this parameters list."""
		if parameters == None: return self
		if type(parameters) == dict:
			for name, value in parameters.items():
				self.add(name, value)
		elif type(parameters) in (tuple, list):
			for v in parameters:
				if type(v) in (tuple, list):
					name, value = v
					self.add(name, value)
				elif type(v) in (str, unicode):
					if v:
						name_value = v.split(":", 1)
						value      = None
						if len(name_value) == 1:
							name = name_value
						else:
							name, value = name_value
						self.add(name.strip(), value.strip())
				else:
					raise Exception("Pair.merge: Unsupported type for merging %s" % (parameters))
		elif type(parameters) in (str, unicode):
			return self.merge(parameters.split("\n"))
		elif isinstance(parameters, Pairs):
			for name, value in parameters.pairs:
				self.add(name, value)
		else:
			raise Exception("Pair.merge: Unsupported type for merging %s" % (parameters))
		return self

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

	def __getitem__( self, k ):
		if type(k) == int:
			return self.pairs[k]
		else:
			return self.get(k)

	def __len__(self):
		return len(self.pairs)

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
	params=None, headers=None, data=None,  cookies=None, mimetype=None ):
		self._method      = method.upper()
		self._url         = url
		self._params      = Pairs(params)
		self._cookies     = Pairs().merge(cookies)
		self._headers     = Pairs(headers)
		self._data        = data
		self._fields      = Pairs(fields)
		self._attachments = []
		if attach: self._attachments.extend(attach)
		# Ensures that the method is a proper one
		if self._method not in METHODS:
			raise Exception("Method not supported: %s" % (method))
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

	STATUS  = 0
	HEADERS = 1
	BODY    = 2

	def __init__( self, session, request ):
		self._client     = session._httpClient
		self._session    = session
		self._request    = request
		self._status     = None
		self._cookies    = Pairs()
		self._newCookies = None
		self._done       = False
		self._responses  = []
		self._failure    = None

	def session( self ):
		"""Returns this transaction session"""
		return self._session

	def request( self ):
		"""Returns this transaction request"""
		return self._request

	def status( self ):
		"""Returns the session status"""
		return self._status

	def fail( self, exception ):
		self._failure = exception
		return self

	def cookies( self ):
		"""Returns this transaction cookies (including the new cookies, if the
		transaction is set to merge cookies)"""
		return self._cookies

	def header( self, name ):
		return self.headers().get(name)

	def rawHeaders( self ):
		return self._responses[-1][self.HEADERS]

	def headers( self ):
		"""Returns the headers received by the response."""
		headers = self._responses[-1][self.HEADERS]
		headers = self._client._parseHeaders(headers)
		return Pairs(headers)

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

	def body( self ):
		"""Returns the response data (implies that the transaction was
		previously done)"""
		if self._responses:
			return self._responses[-1][self.BODY]
		else:
			return None

	def data( self ):
		"""Returns the response data (implies that the transaction was
		previously done)"""
		return self.body()

	def dataAsJSON( self ):
		return json.loads(self.data())

	def asJSON( self ):
		return self.dataAsJSON()

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
		response = None
		# if self._verbose >= 1:
		# 	self._session._log(request.method(), request.url())
		# We merge the session cookies into the request
		request.cookies().merge(self.session().cookies())
		# As well as this transaction cookies
		request.cookies().merge(self.cookies())
		# We send the request as a GET
		if request.method() == GET:
			responses = self._client.GET(
				request.url(),
				headers=request.headers().asHeaders()
			)
		elif request.method() == HEAD:
			responses = self._client.HEAD(
				request.url(),
				headers=request.headers().asHeaders()
			)
		# Or as a POST
		elif request.method() == POST:
			responses = self._client.POST(
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
		self._status     = self._client.status()
		self._newCookies = Pairs(self._client.newCookies())
		self._done       = True
		self._responses += responses
		return self

	def done( self ):
		"""Tells if the transaction is done/complete."""
		return self._done

	# SCRAPING ________________________________________________________________
	def asTree( self ):
		return scrape.HTML.tree(self.data())

	def unjson( self ):
		return json.loads(self.data())

	def query( self, selector ):
		"""Converts the current transaction to an HTML/XML tree and applies
		the given CSS selector query."""
		return self.asTree().query(selector)

	def save( self, path ):
		"""Saves the current transaction data to the current file"""
		with file(path,"wb") as f:
			f.write(self.data())

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
	- 'cache':           Cache contained last requests
	- 'cookies':         List of cookies for this session
	- 'userAgent':       String for this user session agent

	"""

	MAX_TRANSACTIONS = 10
	REDIRECT_LIMIT   = 5
	DEFAULT_RETRIES  = [0.25, 0.5, 1.0, 1.5, 2.0]
	DEFAULT_DELAY    = 1
	CACHE            = None

	def __init__( self, url=None, verbose=0, personality="random", follow=True, do=True, delay=None, cache=None, exceptions=True, client=None ):
		"""Creates a new session at the given host, and for the given
		protocol.
		Keyword arguments::
			'delay':  the range of delay between two requests e.g: (1.5, 3)"""
		self._httpClient      = (client or DEFAULT_HTTP_CLIENT)()
		cache                 = cache if cache else self.CACHE
		if cache: self._httpClient.setCache(cache)
		self._host            = None
		self._port            = 80
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
		self._delay           = delay
		self._headers         = []
		self._throwExceptions = True
		if type(personality) in (unicode,str): personality = Personality.Get(personality)
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
			sys.stderr.write(" ".join(map(str,args)) + "\n")

	def auth( self, user, passwd ):
		"""Adds an HTTP Authentication header to the curent session based on the given
		user and password."""
		self._headers = filter(lambda _:_[0]!="Authorization", self._headers)
		self._headers.append(("Authorization", "Basic " + base64.b64encode(user + ":" + passwd)))
		return self

	def setLogger( self, callback ):
		"""Sets the logger callback (only enabled when the session is set to
		'verbose'"""
		self._onLog = self._httpClient._onLog = callback

	def asFirefox( self ):
		"""Sets this session personality to be Firefox. This returns the
		'Firefox' personaly instance that will be bound to this session, you can
		later change it."""
		return self.setPersonality(Firefox())

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

	def asJSON( self ):
		assert self.last(), "No transaction available."
		return self.last().asJSON()

	def asTree( self ):
		return HTML.tree(self.page())

	def status( self ):
		"""Returns the status of the last transaction. This is an alias for
		`self.last().status()`"""
		assert self.last(), "No transaction available."
		return self.last().status()

	def url( self, suffix=None ):
		"""Returns the URL of the last page. This is an alias for
		`self.last().url()`"""
		if not suffix:
			assert self.last(), "No transaction available."
			return self.last().url()
		else:
			if "://" in suffix:
				return suffix
			elif suffix[0] == "/":
				return "{0}{1}".format(self.rootUrl(), suffix)
			else:
				return "{0}/{1}".format(self.baseUrl(), suffix)

	def baseUrl( self ):
		url = self.url()
		return url.rsplit("/", 1)[0]

	def rootUrl( self ):
		url   = self.url()
		proto, path =  url.rsplit("://", 1)
		return "{0}://{1}".format(proto, path.split("/",1)[0])

	def form( self, name=None ):
		"""Returns the first form declared in the last transaction response data."""
		form = self.forms(name)
		if not form: return None
		if name is None:
			if form:
				return form.values()[0]
			else:
				return None
		return form

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

	def head( self, url="/", params=None, headers=None, follow=None, do=None, cookies=None, retry=[], cache=True ):
		return self.get(url=url, params=params, headers=headers, follow=follow, do=do, cookies=cookies, retry=retry, method=HEAD, cache=cache)

	def get( self, url="/", params=None, headers=None, follow=None, do=None, cookies=None, retry=[], method=GET, cache=True):
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
		request     = self._createRequest( url=url, params=params, headers=headers, cookies=cookies, method=method )
		transaction = Transaction( self, request )
		self.__addTransaction(transaction)
		# FIXME: Redo on timeout
		if do:
			# We do the transaction
			# set a delay to do the transaction if _delay is specified
			if self._delay: time.sleep(random.uniform(*self._delay))
			# ensure that transaction.do retries after a fail
			retry = retry or self.DEFAULT_RETRIES
			for i,r in enumerate(retry):
				try:
					transaction.do()
					break
				except Exception as e:
					if isinstance(e, httplib.IncompleteRead) or isinstance(e, socket.timeout):
						# We retry only on socket timeout or incomplete read
						if i >= len(retry):
							return self._failTransaction(transaction, e)
						else:
							time.sleep(r)
					else:
						return self._failTransaction(transaction, e)
			if self.MERGE_COOKIES: self._cookies.merge(transaction.newCookies())
			visited   = [url]
			iteration = 0
			while transaction.redirect() and follow and iteration < self.REDIRECT_LIMIT:
				redirect_url = self.__processURL(transaction.redirect(), store=False)
				if not (redirect_url in visited):
					visited.append(redirect_url)
					transaction = self.get(redirect_url, headers=headers, cookies=cookies, do=True, method=method, follow=False)
					iteration  += 1
				else:
					break
		return transaction

	def _failTransaction( self, transaction, exception ):
		transaction.fail(exception)
		if self._throwExceptions:
			raise exception
		return transaction

	def post( self, url=None, params=None, data=None, mimetype=None,
	fields=None, attach=None, headers=None, follow=None, do=None, cookies=None, retry=[], cache=True):
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
			data=data, mimetype=mimetype, headers=headers, cookies=cookies
		)
		transaction = Transaction( self, request )
		self.__addTransaction(transaction)
		if do:
			# We do the transaction
			# set a delay to do the transaction if _delay is specified
			if self._delay: time.sleep(random.uniform(*self._delay))
			# ensure that transaction.do retries after a fail
			retry = retry or self.DEFAULT_RETRIES
			for i,r in enumerate(retry):
				try:
					transaction.do()
					break
				except httplib.IncompleteRead as e:
					if i >= len(retry):
						raise e
					else:
						time.sleep(r)
			if self.MERGE_COOKIES: self._cookies.merge(transaction.newCookies())
			# And follow the redirect if any
			visited = [url]
			while transaction.redirect() and follow:
				redirect_url = self.__processURL(transaction.redirect(), store=False)
				if not (redirect_url in visited):
					visited.append(redirect_url)
					transaction = self.post(redirect_url, data=data, mimetype=mimetype, fields=fields, attach=attach, headers=headers, cookies=cookies, do=True)
				else:
					break
		return transaction

	def submit( self, form, values={}, attach=[], action=None,  method=POST,
	do=None, cookies=None, strip=True ):
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
			return self.post( url, fields=fields, attach=attach, do=do, cookies=cookies )
		elif method in (GET, HEAD):
			assert not attach, "Attachments are incompatible with GET submission"
			return self.get( url,  params=fields, do=do, cookies=cookies )
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

	def asJSON( self ):
		return self.last().asJSON()

	def save(self, path, transaction=None):
		"""Saves the page from the given transaction (default it 'last()') to
		the given file."""
		if transaction is None: transaction = self.last()
		d = transaction.data()
		f = file(path,'w')
		f.write(d)
		f.close()

	def preview( self, transaction=None ):
		"""Opens a web browser to preview the request."""
		if transaction is None: transaction = self.last()
		ext  = transaction.headers().get("ContentType") or "text/html"
		ext  = ext.strip().split(";",1)[0].split("/")[-1]
		path = tempfile.mktemp(prefix="wwwclient-", suffix="."+ext)
		self.save(path, transaction)
		webbrowser.open("file://" + path)
		time.sleep(5)
		os.unlink(path)

	def __processURL( self, url, store=True ):
		"""Processes the given URL, by storing the host and protocol, and
		returning a normalized, absolute URL"""
		# FIXME: Should infer the URL based on the current URL
		old_url = url
		if url == None and not self._transactions: url = "/"
		if url == None and self._transactions: url = self.last().request.url()
		proto_rest = url.split("://",1)
		if len(proto_rest) == 2 and proto_rest[0].find("/") == -1:
			# If the URL was given with a protocol, then we might change server
			protocol, host, path, parameters, query, fragment =  urlparse.urlparse(url)
		else:
			# Otherwise we expect to be on the same server (and then just the
			# path is given)
			assert self._host, "No host was given to url: {0}".format(url)
			protocol, host, path, parameters, query, fragment =  urlparse.urlparse(
				"%s://%s:%s%s" % (
					(self._protocol or HTTP),
					self._host,
					self._port or 80,
					url[0] == "/" and url or ("/" + url)
			))
		if store:
			if   protocol == "http":  self._protocol = protocol = HTTP
			elif protocol == "https": self._protocol = protocol = HTTPS
		port = None
		if host:
			host = host.split(":")
			if len(host) == 1:
				host = host[0]
			else:
				port = host[1]
				host = host[0]
			if store:
				self._host = host
				self._port = port
		# We recompose the url
		if port and port != 80 and port != "80":
			url = "%s://%s:%s" % (protocol, host, port)
		else:
			url = "%s://%s" % (protocol, host)
		if   path and path[0] == "/": url += path
		elif path:      url += "/" + path
		else:           url += "/"
		if parameters:  url += ";" + parameters
		if query:       url += "?" + query
		if fragment:    url += "#" + fragment
		return url

	def _createRequest( self, **kwargs ):
		# We copyt the session headers (ie. authentication)
		kwargs["headers"] = (kwargs.get("headers") or []) + self._headers
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

	@classmethod
	def Get( self, agent ):
		if agent == "random":
			return self.Get(agents.pickAgent())
		elif agent.lower() == "firefox":
			return Firefox()
		else:
			return self(agent)

	def __init__( self, agent ):
		self.agent = agents.pickLatest(agent)

	def userAgent( self ):
		return self.agent[-1]

	def apply( self, request ):
		pass

class Firefox(Personality):
	"""Simulates the way Firefox would behave."""

	def __init__( self ):
		Personality.__init__(self, "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:11.0) Gecko/20100101 Firefox/11.0")

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
