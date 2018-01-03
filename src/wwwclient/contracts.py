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
# Creation  : 18-Jul-2006
# Last mod  : 18-Jul-2006
# -----------------------------------------------------------------------------

import browse, scrape

__doc__ = """\
The contract module allows to express simple test case that allow to check
particular responses. This enables easy verification of an API, as well as
detection of modfications of an existing website API.
"""

# -----------------------------------------------------------------------------
#
# CONTRACT
#
# -----------------------------------------------------------------------------

def provides(*names):
	"""Decorates a contract test method, telling that it provides a particular
	resource, that may be required by another test."""
	def _(f):
		if not hasattr(f, "_provides"): f._provides = []
		for name in names:
			if not name in f._provides:
				f._provides.append(name)
		return f
	return _

def depends(*names):
	"""Decorates a contract test method, telling that it depends on a particular
	resource."""
	def _(f):
		if not hasattr(f, "_depends"): f._depends = []
		for name in names:
			if not name in f._depends: 
				f._depends.append(name)
		return f
	return _

class ContractError(Exception): pass
class Contract:
	"""A contract is like a unit test case, but for a website. Each contract has
	its own browsing session and scraping tools, which can be used by the
	various test methods."""

	def __init__( self ):
		self.session   = None
		self.HTML      = None
		self.errors    = None
		self.provided  = None
		self.completed = None

	def setup( self,  ):
		"""This method creates the @session and @HTML attribute.
		It is called just before the contract is run."""
		self.session   = browse.Session()
		self.HTML      = scrape.HTMLTools()
		self.errors    = []
		self.warnings  = []
		self.provided  = []
		self.tests     = self._getTests()
		self.remaining = list(self.tests)
		self.completed = []

	def _getTests( self ):
		res = []
		for key in dir(self):
			if key.startswith("test"):
				res.append(getattr(self, key))
		return res

	def _dependenciesMet( self, test ):
		if hasattr(test, "_depends"):
			for dep in test._depends:
				if dep not in self.provided: return False
		return True
	
	def _provide( self, test ):
		if hasattr(test, "_provides"):
			for prov in test._provides:
				if prov not in self.provided:
					self.provided.append(prov)

	def _nextTest( self ):
		"""Returns the next test that can be passed, or None, if no test was
		found"""
		for remaining in self.remaining:
			if self._dependenciesMet(remaining):
				res = remaining
				self.remaining.remove(res)
				return res
		return None

	def run( self ):
		"""Sets up and run the tests."""
		self.setup()
		while True:
			error = False
			test  = self._nextTest()
			if test == None: break
			name  = test.__name__[4:]
			try:
				test()
			except ContractError, e:
				error = e
			if error:
				print "%-20s [FAILED] (%s)" % (name, error)
			else:
				print "%-20s [OK]" % (name)
				self._provide(test)
				self.completed.append(test)
		print "--"
		percent = int(100.0 * float(len(self.completed)) / float(len(self.tests)))
		print "Completed            %3d%%" % (percent)

	def error( self, reason):
		self.errors.append((self.session.url(), reason))
		raise ContractError(self.session.url(), reason)
	
	def warning( self, reason ):
		self.warnings.append((self.session.url(), reason))

	def expect( self, value, message ):
		if not value: self.error(message)

	def expectForm( self, formName, formFields=() ):
		"""Expects a from with the given name and given fields to be present in
		the current transaction data."""
		forms = self.HTML.forms(self.session.last().data())
		if not forms:
			self.error("No form available")
		elif not forms.has_key(formName):
			self.error("Expected form '%s': got %s" % (formName, ", ".join(forms.keys())))
		elif formFields:
			form        = forms[formName]
			not_found   = []
			form_fields = form.fields(namesOnly=True)
			for form_field in formFields:
				if form_field not in form_fields:
					not_found.append(form_field)
			if not_found:
				self.error("Fields not found: %s, got %s" % (not_found, form_fields))
		return forms[formName]

	def expectURL( self, url ):
		"""Expects the current URL to be like the given URL"""
		if not self.session.last().url() == url:
			self.error(
				"Unexpected URL: got %s, expected %s" % (
					repr(self.session.last().url()),
					repr(url)
			))

	def expectText( self, contains=() ):
		"""Expects various criteria on the current transaction data, once
		stripped out of HTML data."""
		text = self.session.last().data()
		if type(contains) in (str,unicode): contains = [contains]
		for c in contains:
			if text.find(c) == -1:
				self.error("String not found: %s" % (repr(c)))

# EOF - vim: tw=80 ts=4 sw=4 noet
