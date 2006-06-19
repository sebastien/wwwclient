import httplib, urllib, mimetypes
import re

__version__ = "2.0"

HTTP    = httplib.HTTPConnection
HTTPS   = httplib.HTTPSConnection

GET     = "GET"
POST    = "POST"
HEAD    = "HEAD"
METHODS = (GET, POST, HEAD)

RE_HEADER = re.compile(r"(.*?):\s*(.*?)\s*$")
RE_COOKIE = re.compile(r"(.*);?")

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
		else:
			for name, value in parameters.pairs:
				self.add(name, value)

	def encode( self ):
		"""Returns an URL-encoded version of this parameters list."""
		return urllib.urlencode(self.pairs)
	
	def __repr__(self):
		return repr(self.pairs)

class Request:
	"""The Request object encapsulates an HTTP request so that it is easy to
	specify headers, cookies, data and attachments."""

	BOUNDARY = "---------------------------7d418b1ee20fc0"
	
	def __init__( self, method=GET, url="/", params=None ):
		self._url        = url
		self._method     = method.upper()
		self._data       = None
		self._dataType   = "text/plain"
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
		if not mime: mime = "text/plain"
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
	
	def header( self, name, value=urllib ):
		"""Gets or set the given header."""
		if value == urllib:
			return self._headers.get(name)
		else:
			self._headers[name] = str(value)

	def headers( self ):
		"""Returns the headers for this request."""
		headers = {}
		headers.update(self._headers)
		# Takes care of cookies
		headers.setdefault('Cookie', ";".join([ "%s=%s" % (k,urllib.quote(v)) for k,v in self.cookies.pairs]))
		# Takes care of content type
		if self.attachments:
			headers.setdefault("Content-Type", "multipart/form-data; boundary=%s" % (Request.BOUNDARY))
		elif self._method == POST:
			headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
		# Takes care of content length
		body = self.body()
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

class Transaction:
	"""A transaction encaspulates a request and its responses."""

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
		print "Requesting:", self.request.method(), ":", self.request.url()
		# We send the request
		connection = self.session.protocol(self.session.host)
		connection.request(self.request.method(), self.request.url(),
		self.request.body(), self.request.headers() )
		# And get the response
		self.response = connection.getresponse()
		self.status   = self.response.status
		self.data  = self.response.read()
		connection.close()
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
		# We merge the cookies if necessary
		if mergeCookies:
			self.session.cookies.merge(self.cookies)
		# We take care of URL redirection
		if redirect_url != None:
			self.redirect = self.session.get(redirect_url, do=False)
		self.done = True

class Session:
	MAX_TRANSACTIONS = 10

	def __init__( self, host, protocol=HTTP ):
		if host.startswith("http://"):
			protocol = HTTP
			host     = host[len("http://"):]
		if host.startswith("https://"):
			protocol = HTTPS
			host     = host[len("https://"):]
		self.host         = host
		self.protocol     = protocol
		self.transactions = []
		self.cookies      = Parameters()

	def last( self ):
		return self.transactions[-1]

	def addTransaction( self, transaction ):
		if len(self.transactions) > self.MAX_TRANSACTIONS:
			self.transactions = self.transactions[1:]
		self.transactions.append(transaction)

	def get( self, url=None, params=None, do=True ):
		if not url: url = "/"
		if not url.startswith("/"): url = "/" + url
		request = Request( url=url, params=params )
		transaction = Transaction( self, request )
		self.addTransaction(transaction)
		if do: transaction.do()
		return transaction

	def post( self, url=None, params=None, do=True ):
		if not url: url = self.last().request.url()
		if not url.startswith("/"): url = "/" + url
		request = Request( method=POST, url=url, params=params )
		transaction = Transaction( self, request )
		self.addTransaction(transaction)
		if do: transaction.do()
		return transaction

# Events
# - Redirect
# - New cookie
# - Success
# - Error
# - Timeout
# - Exception

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
