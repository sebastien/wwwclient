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

import re

RE_SPACES    = re.compile("\s+")
RE_FORMDATA  = re.compile("<(form|input)", re.I)
RE_HTMLSTART = re.compile("</?(\w+)",      re.I)
RE_HTMLEND   = re.compile(">")

HTML_OPEN    = 0
HTML_CLOSE   = 1

# -----------------------------------------------------------------------------
#
# FORM
#
# -----------------------------------------------------------------------------

class FormException(Exception): pass
class Form:
	"""A simple interface to forms, returned by the scraper. Forms can be easily
	filled and their values (@values) can be given as parameters to the @browse
	module."""

	def __init__( self, name, action=None ):
		self.name   = name
		self.action = action
		self.inputs = []
		self.values = {}

	def fields( self, namesOnly=False ):
		res = filter(lambda f:f.get("type") != "submit", self.inputs)
		if namesOnly: res = tuple(f.get("name") for f in res)
		return res
	
	def actions( self, namesOnly=False ):
		res = filter(lambda f:f.get("type")=="submit", self.inputs)
		if namesOnly: res = tuple(f.get("name") for f in res)
		return res

	def clear( self ):
		"""Clears the existing values set in this form, and returns them."""
		old_values = self.values
		self.values = {}
		return old_values

	def fill( self, **values ):
		field_names = map(lambda f:f.get("name"), self.fields())
		for name, value in values.items():
			self.values[name] = value

	def parameters( self ):
		"""Returns a list of (key,value) respecting the original input order."""
		res   = []
		names = []
		for field in self.inputs:
			name = field.get("name")
			names.append(name)
			if not name: continue
			if self.values.get(name) == None: continue
			res.append((name, self.values.get(name)))
		# The user may have added specific parameters that do not correspond to
		# a specific input, so we ensure that they are added here
		for key, value in self.values.items():
			if key not in names:
				res.append((key, value))
		return res

	def submit( self, action=None, **values ):
		"""Submits this form with the given action and given values."""
		self.fill(**values)
		parameters  = []
		field_names = self.fields(namesOnly=True)
		# We fill values that were initialized
		for key in field_names:
			value = self.values.get(key)
			if self.values.has_key(key):
				parameters.append((key, value))
		# And add values that do not correspond to any field
		for key, value in values.items():
			if key not in field_names:
				parameters.append((key, value))
		# if action: parameters.append((action, self.values.get(action)))
		return parameters

	def _prefill( self ):
		"""Sets the default values for this form."""
		for inp in self.inputs:
			name  = inp.get("name")
			value = inp.get("value")
			if name and value: self.values[name] = value
	
	def __repr__( self ):
		return repr(self.inputs)

# -----------------------------------------------------------------------------
#
# HTML PARSING FUNCTIONS
#
# -----------------------------------------------------------------------------

class HTML:
	"""This class contains a set of tools to process HTML text data easily. This
	class can operate on a full HTML document, or on any subset of the
	document."""

	@staticmethod
	def nextTag( html, offset=0 ):
		if offset >= len(html) - 1: return None
		m = RE_HTMLSTART.search(html, offset)
		if m == None:
			return None
		n = RE_HTMLEND.search(html, m.end())
		if n == None:
			return HTML.nextTag(html, m.end())
		if m.group()[1] == "/": tag_type = HTML_CLOSE
		else: tag_type = HTML_OPEN
		return (tag_type, m.group(1), m.start(), m.end(), n.start()), n.end()

	@staticmethod
	def iterate( html ):
		offset = 0
		end    = False
		while not end:
			tag = HTML.nextTag(html, offset)
			if tag == None:
				yield html[offset:]
				end = True
			else:
				tag, tag_end_offset = tag
				tag_type, tag_name, tag_start, attr_start, attr_end = tag
				if tag_start > offset: yield html[offset:tag_start]
				yield tag
				offset = tag_end_offset

	@staticmethod
	def textOnly( data ):
		"""Strips the text or list (resulting from an HTML.iterate) from HTML
		tags, so that only the text remains."""
		if type(data) in (tuple, list):
			return "".join([text for text in data if type(text) not in (list,tuple)])
		else:
			return "".join([text for text in HTML.iterate(data) if type(text) not in (list, tuple)])

	@staticmethod
	def parseAttributes(text, attribs = None):
		if attribs == None: attribs = {}
		eq = text.find("=")
		# There may be attributes without a trailing =
		# Like  ''id=all type=radio name=meta value="" checked''
		if eq == -1:
			space = text.find(" ")
			if space == -1:
				name = text.strip()
				if name: attribs[name] = None
				return attribs
			else:
				name = text[:space].strip()
				if name: attribs[name] = None
				return parseAttributes(text[space+1:], attribs)
		else:
			sep = text[eq+1]
			if   sep == "'": end = text.find( "'", eq + 2 )
			elif sep == '"': end = text.find( '"', eq + 2 )
			else: end = text.find(" ", eq)
			# Did we reach the end ?
			name = text[:eq]
			if end == -1:
				value = text[eq+1:]
				if value and value[0] in ("'", '"'): value = value[1:-1]
				else: value = value.strip()
				attribs[name.lower()] = value
				return attribs
			else:
				value = text[eq+1:end+1]
				if value[0] in ("'", '"'): value = value[1:-1]
				else: value = value.strip()
				attribs[name.lower()] = value
				return HTML.parseAttributes(text[end+1:].strip(), attribs)

# -----------------------------------------------------------------------------
#
# SCRAPER
#
# -----------------------------------------------------------------------------

class ScraperException(Exception): pass
class Scraper:
	
	def forms( self, html ):
		"""Will extract the forms from the HTML document in a way that tolerates
		inputs outside of forms (this happens sometime). This function is very
		fast, because it only uses regexes to search for tags within the
		document, so there is no need to parse the HTML."""
		if not html: raise ScraperException("No data")
		i       = 0
		end     = len(html)
		matches = []
		# We get all the form data
		while i < end:
			match = RE_FORMDATA.search(html, i)
			if not match: break
			matches.append(match)
			i = match.end()
		# And we create the forms tree
		current_form  = None
		forms         = {}
		default_count = 0
		for match in matches:
			tag_end    = html.find(">", match.end())
			name       = match.group(1).lower()
			attributes = HTML.parseAttributes(html[match.end():tag_end].strip())
			if name == "form":
				form_name = attributes.get("name")
				if not form_name:
					form_name = "default%s" % ( default_count )
					default_count += 1
				current_form = Form(form_name, attributes.get("action"))
				forms[current_form.name] = current_form
			elif name == "input":
				assert current_form
				# TODO: Make this nicer
				js = filter(lambda s:s[0].startswith("on"), attributes.items())
				if js:
					print "Warning: Form may contain JavaScript: ", current_form.name, "input", attributes.get("name"), js
				current_form.inputs.append(attributes)
			else:
				raise Exception("Unexpected tag: " + name)
		# Prefills the forms
		for form in forms.values(): form._prefill()
		return forms

# EOF
