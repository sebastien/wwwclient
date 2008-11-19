#!/usr/bin/env python
# Encoding: iso-8859-1
# -----------------------------------------------------------------------------
# Project   : WWWClient
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre <sebastien@xprima.com>
# -----------------------------------------------------------------------------
# License   : GNU Lesser General Public License
# Credits   : Xprima.com
# -----------------------------------------------------------------------------
# Creation  : 12-Sep-2006
# Last mod  : 26-Jul-2008
# -----------------------------------------------------------------------------

import re

RE_FORMDATA  = re.compile("<(form|input|select|option|textarea)", re.I)

# -----------------------------------------------------------------------------
#
# FORM
#
# -----------------------------------------------------------------------------

class FormException(Exception): pass
class Form:
	"""A simple interface to forms, returned by the scraper. Forms can be easily
	filled and their values (@values) can be given as parameters to the @browse
	module.
	
	A form has:

	- a _single action_
	- a _list of inputs_ which are dicts of equivalent HTML element attributes.
	  For elements such as `select` or `textarea`, the input `type` property is
	  set to the actual element type.
	- a _list of values_ which will be associated with values when filling the
	  form.
	
	Form values are cleanly separated from their inputs, so that you can simply
	clear the values to resubmit the form.
	"""

# TODO: Add STRICT mode for form that checks possible values/action/field names

	def __init__( self, name, action=None ):
		self.name    = name
		self.action  = action
		self.inputs  = []
		self.values  = {}
		self._fields = {}

	def _addInput( self, inputDict ):
		"""Private function used by the `parseForms` function to add an input to
		this form. The input will be added to the `inputs` list and to the
		`_fields` dict."""
		self.inputs.append(inputDict)
		if inputDict.get("name"):
			self._fields[inputDict["name"]] = inputDict

	def fields( self, namelike=None, namesOnly=False ):
		"""Returns that list of inputs (or input names if namesOnly is True) that
		can be assigned a value (checkboxes, inputs, text areas, etc)."""
		res = filter(lambda f:f.get("type") != "submit", self.inputs)
		if namelike:
			namelike = re.compile(namelike)
			res = filter(lambda f:namelike.match(f.get("name")), res)
		if namesOnly: res = tuple(f.get("name") for f in res)
		return res

	def fieldNames( self ):
		"""Alias to 'fields(nameOnly=True)'. Returns the name of the fields of
		this form."""
		return self.fields(namesOnly=True)

	def field( self, name, caseSenstitive=True ):
		"""Returns the field with the given name, or None if it does not
		exist."""
		if not caseSenstitive: name = name.lower()
		for field in self.inputs:
			field_name = field.get("name")
			if field_name is None: continue
			if not caseSenstitive: field_name = field_name.lower()
			if field_name == name:
				return field
		return None
	
	def actions( self, namelike=None, namesOnly=False ):
		"""Returns the list of inputs (or input names if namesOnly is True) that
		correspond to form action buttons."""
		res = filter(lambda f:f.get("type")=="submit", self.inputs)
		if namelike:
			if namelike in (str,unicode): namelike = re.compile(namelike)
			res = filter(lambda f:namelike.match(f.get("name")), res)
		if namesOnly: res = tuple(f.get("name") for f in res)
		return res

	def clear( self ):
		"""Clears the existing values set in this form, and returns them."""
		old_values = self.values
		self.values = {}
		return old_values

	def fill( self, **values ):
		"""Fills this form with the given values."""
		# field_names = map(lambda f:f.get("name"), self.fields())
		for name, value in values.items():
			# FIXME: Check that the name exists in the form
			self.values[name] = value
		return self
	
	def set( self, name, value ):
		"""Sets the given form value. This modified the values within the form,
		and not the fields directly."""
		field = self._fields.get(name)
		if field:
			field_type = field.get("type")
			if field_type and field_type.lower() == "checkbox":
				if    value is None: pass
				elif  value: value = "on"
				else: value = "off"
		else:
			# FIXME: Issue a warning, because the field did not exist before
			pass
		self.values[name] = value

	def unset( self, name ):
		"""This unsets the given value from this form values. The effect will be
		that that the named input default value will be used instead of a
		user-provided one."""
		del self.values[name]

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

	def submit( self, action=None, encoding="latin-1", strip=True, **values ):
		"""Submits this form with the given action and given values. This
		basically takes all the default values set within this form, replacing
		them with the set or given values (given as keywords), and returns a list of
		(key, value) pairs that represent the parameters that should be encoded
		in the response.
		
		In this repsect, the submit method does not do the actual submission,
		but rather prepares the data for submission.

		Also, note that _submission does not mutate the form_, it simply creates
		a list of parameters suitable for creating the body of a post request.
		"""
		self.fill(**values)
		parameters  = []
		# We get the field and action names
		field_names  = []
		# We fill values that were initialized
		for field in self.fields():
			key = field.get("name")
			field_names.append(key)
			value = self.values.get(key) or field.get("value") or ""
			if strip and not value: continue
			if type(value) == unicode: value = unicode(value).encode(encoding)
			parameters.append((key, value))
		# And add values that do not correspond to any field
		for key, value in values.items():
			if key not in field_names:
				if strip and not value: continue
				if type(value) == unicode: value = unicode(value).encode(encoding)
				parameters.append((key, value))
		if action:
			if action not in self.actions(namesOnly=True):
				raise FormException("Action not available: %s, in form %s: choose from %s" %
				(action, self.name, self.actions(namesOnly=True)))
			parameters.append((action, self.values.get(action)))
		return parameters

	def _prefill( self ):
		"""Sets the default values for this form."""
		for inp in self.inputs:
			name  = inp.get("name")
			value = inp.get("value")
			if name and value: self.values[name] = value
	
	def asText( self ):
		"""Returns a pretty-printed text representation of this form. This
		representation is very useful when it comes to analysing web pages."""
		# TODO: Rewrite Form.asText, it is ugly.
		cut     = 20
		res     = "FORM: %s (%s)\n" % (self.name, self.action)
		rows    = []
		max_row = []
		def cut_row( a ):
			a = str(a)
			if len(a) > cut: return a[:cut - 3] + "..."
			else: return a
		for inp in self.inputs:
			rows.append([inp.get("type"), inp.get("name"), self.values.get(inp.get("name")), inp.get("value")])
			rows[-1][2] = cut_row(rows[-1][2])
			rows[-1][3] = cut_row(rows[-1][3])
			for i in range(len(rows[-1])):
				if len(max_row) == len(rows[-1]):
					max_row[i] = max(max_row[i], len(str(rows[-1][i])))
				else:
					max_row.append(len(str(rows[-1][i])))
		format  = "%-" + str(max_row[0]) + "s | %-" + str(max_row[1])  + "s"
		format += "= %-" + str(max_row[2]) + "s  %" + str(max_row[3]) + "s"
		rows.sort(lambda a,b:cmp(a[0:2], b[0:2]))
		for row in rows:
			if row[2] == row[3]:
				state   = row[3]
				default = "(default)"
			else:
				state   = row[2]
				default = ""
			if state == "None": state = ""

			res += format % (row[0], row[1], state, default)
			res += "\n"
		return res

	def __repr__( self ):
		return "<form:name='%s' action='%s' fields=%s>" % (self.name, self.action, repr(self.inputs))

def parseForms( scraper, html ):
	"""Will extract the forms from the HTML document in a way that tolerates
	inputs outside of forms (this happens sometime). This function is very
	fast, because it only uses regexes to search for tags within the
	document, so there is no need to parse the HTML.
	
	Currently form inputs, select and option are supported.
	"""
	if not html: raise Exception("No data")
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
	current_form   = None
	current_select = None
	forms          = {}
	default_count  = 0
	for match in matches:
		# We get the end of the tag, which may be with or without a trailing
		# /
		tag_end    = html.find(">", match.end())
		if html[tag_end-1] == "/": tag_end -=1
		name       = match.group(1).lower()
		attributes = scraper.parseAttributes(html[match.end():tag_end].strip())
		if name == "form":
			form_name = attributes.get("name")
			if not form_name:
				form_name = "default%s" % ( default_count )
				default_count += 1
			# We do not replace an existing frame (which may happen if there
			# is two <form name='...> with the same name (yes, this can
			# happen !)
			if not forms.has_key(form_name):
				if not attributes.get("action"):
					action= None
				else:
					action= scraper.expand(attributes.get("action"))
				current_form = Form(form_name, action)
				forms[current_form.name] = current_form
		elif name == "input":
			#assert current_form
			# TODO: Make this nicer
			# js = filter(lambda s:s[0].startswith("on"), attributes.items())
			# FIXME: Adda a warnings interface
			#if js:
			#	print "Warning: Form may contain JavaScript: ", current_form.name, "input", attributes.get("name"), js
			if not current_form:
				# Found an INPUT type without FORM.. maybe JavaScript tricks
				current_form= Form("no_form")
				forms[current_form.name] = current_form
			current_form._addInput(attributes)
		elif name == "select":
			assert current_form
			current_select = attributes
			current_select["type"] = "select"
			current_form._addInput(current_select)
		elif name == "option":
			assert current_form
			assert current_select
			selected = attributes.get("selected") or ""
			if current_select == None:
			#	print "Warning: Option outside of select: ", current_form.name
				continue
			if selected.lower() == "selected":
				current_select["value"] = attributes["value"]
			else:
				# TODO: We ignore them for now
				pass
		elif name == "textarea":
			text_end = html.find("</textarea", match.end())
			text = html[tag_end+1:text_end]
			attributes["type"] = "textarea"
			attributes["value"] = text
			current_form._addInput(attributes)
		else:
			raise Exception("Unexpected tag: " + name)
	# Prefills the forms
	for form in forms.values():
		form._prefill()
	return forms

# EOF - vim: tw=80 ts=4 sw=4 noet
