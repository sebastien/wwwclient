#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : WWWClient - Python client Web toolkit
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre <sebastien@xprima.com>
# Creation  : 19-Jun-2006
# Last mod  : 22-Jun-2006
# -----------------------------------------------------------------------------

import re, string, htmlentitydefs

RE_SPACES    = re.compile("\s+")
RE_FORMDATA  = re.compile("<(form|input)", re.I)
RE_HTMLSTART = re.compile("</?(\w+)",      re.I)
RE_HTMLEND   = re.compile("/?>")
RE_HTMLLINK  = re.compile("<[^<]+(href|src)\s*=\s*('[^']*'|\"[^\"]*\"|[^ ]*)", re.I)

RE_HTMLCLASS = re.compile("class\s*=\s*['\"]?([\w\-_\d]+)", re.I)
RE_HTMLID    = re.compile("id\s*=\s*['\"]?([\w\-_\d]+)", re.I)
RE_HTMLHREF  = re.compile("href\s*=\s*('[^']*'|\"[^\"]*\"|[^ ]*)", re.I)

RE_SPACES    = re.compile("\s+", re.MULTILINE)

HTML_OPEN    = "<tag>"
HTML_CLOSE   = "</tag>"
HTML_SINGLE  = "<tag />"

KEEP_ABOVE    = "+"
KEEP_SAME     = "="
KEEP_BELOW    = "-"


# -----------------------------------------------------------------------------
#
# HTML TREE
#
# -----------------------------------------------------------------------------

class Node:

	TEXT = "#text"
	ROOT = "#root"

	def __init__( self, name="#text", attributes=None, parent=None,
	children=None, text=None, html=None, indice=None ):
		if attributes == None: attributes = {}
		if children   == None: childrent  = []
		self.name       = name
		self.attributes = attributes
		self.children   = children
		self.parent     = parent
		self.text       = text
		self.indice     = indice

	def append( self, child ):
		if self.children == None: self.children = []
		self.children.append(child)

	def match( self, name=None, names=None, attributes={} ):
		"""Matches the given name agains the given criteria"""
		# We ensure the names
		if name:
			if not names: names = []
			if type(names) != list: names = list(names)
			names.append(name)
		# We try to match the node name
		if names and not self.name in names: return False
		# We try to match for attributes
		if attributes and not self.attributes: return False
		for attr, val in attributes.items():
			this_val = self.attributes.get(attr)
			if val != None and this_val != val: return False
		return True
	
	def filter( self, name=None, names=None, attributes={} ):
		"""Iterates through the direct children that match the given
		criteria."""
		if self.children:
			for c in self.children:
				if c.match(name=name, names=names, attributes=attributes):
					yield c

	def html(self, norm=False):
		if self.name == Node.TEXT:
			return RE_SPACES.sub(" ",self.text)
		if self.name == Node.ROOT:
			return "".join((c.html() for c in self.children))
		else:
			html_attributes = []
			if self.attributes:
				for a,v in self.attributes.items():
					if v == None:
						html_attributes.append(a)
					else:
						if   v.find('"') == -1: v = '"%s"' % (v)
						else: v = "'%s'" % (v)
						html_attributes.append("%s=%s" % (a,v))
			html_attributes = " ".join(html_attributes)
			if not self.children:
				return  "<%s %s/>" % (self.name, html_attributes)
			else:
				html_children   = "".join((c.html() for c in self.children))
				return "<%s %s>%s</%s>" % (self.name, html_attributes,
				html_children, self.name)
	
	def tags( self, name=None, names=None, attributes={} ):
		"""Iterates through all the subset tags that match the given criteria."""
		if self.match(name=name, names=names,attributes=attributes):
			yield self
		if self.children:
			for c in self.children:
				for r in c.tags(name=name, names=names, attributes=attributes):
					yield r

	def asString( self ):
		if self.indice != None: prefix = "%-4d" % (self.indice)
		else: prefix = ""
		# If this is a text node
		if self.name == Node.TEXT:
			return prefix + "#text:" + repr(self.text)
		# If this is a regular node
		res = prefix
		if self.attributes:
			res += "%s: %s" % (self.name, " ".join(u"%s=%s" % (k,repr(v)) for k,v in self.attributes.items()))
		else:
			res += self.name
		if self.children:
			for c in self.children:
				res += "\n"
				for line in unicode(c.asString()).split("\n"):
					res += line[:len(prefix)] + "| " + line[len(prefix):] + "\n"
				res = res[:-1]
		return res
	
	def __str__( self ):
		return self.asString()

# -----------------------------------------------------------------------------
#
# HTML PARSING FUNCTIONS
#
# -----------------------------------------------------------------------------

LEVEL  = 0
TYPE   = 1
NAME   = 2
START  = 3
END    = 4
ASTART = 5
AEND   = 6

class HTMLTools:
	"""This class contains a set of tools to process HTML text data easily. This
	class can operate on a full HTML document, or on any subset of the
	document."""

	def __init__( self ):
		self.LEVEL_ACCOUNT = [ "html", "head", "body", "div", "table", "tr", "td" ]

	def nextTag( self, html, offset=0 ):
		"""Finds the next tag in the given HTML text from the given offset. This
		returns (tag type, tag name, tag start, attributes start, attributes
		end) and tag end or None."""
		if offset >= len(html) - 1: return None
		m = RE_HTMLSTART.search(html, offset)
		if m == None:
			return None
		n = RE_HTMLEND.search(html, m.end())
		if n == None:
			return self.nextTag(html, m.end())
		if m.group()[1] == "/": tag_type = HTML_CLOSE
		elif n.group()[0] == "/": tag_type = HTML_SINGLE
		else: tag_type = HTML_OPEN
		return (tag_type, m.group(1), m.start(), m.end(), n.start()), n.end()

	def iterate( self, html, write=None, closeOn=() ):
		"""Iterates on the html document and yields a string for text content or
		a tuple (level, type, name, start, attrstart, attrend) corresponding to
		the tag level (number of parents), tag type (HTML_OPEN or HTML_CLOSE),
		tag start and end offsets, attributes start and end offsets."""
		offset   = 0
		level    = 0 
		end      = False
		last     = None
		parents  = []
		sequence = []
		if closeOn: closeOn = list(closeOn)
		keep_sequence = closeOn and len(closeOn) or 0
		while not end:
			tag = self.nextTag(html, offset)
			if tag == None:
				yield html[offset:]
				end = True
			else:
				tag, tag_end_offset = tag
				tag_type, tag_name, tag_start, attr_start, attr_end = tag
				tag_name_lower      = tag_name.lower()
				# We update the keep sequence, which is the sequence of last tag
				# names
				if keep_sequence:
					while len(sequence) > keep_sequence -1: sequence = sequence[1:]
					sequence.append(tag_name_lower)
				# There may be text inbetween
				if tag_start > offset: yield html[offset:tag_start]
				# We decrement the level if necessary
				if tag_name_lower in self.LEVEL_ACCOUNT and tag_type == HTML_CLOSE:
					if tag_name_lower in parents:
						while parents[-1] != tag_name_lower:
							level -= 1
							parents.pop()
						level -= 1
						parents.pop()
				# We process the encountered tag
				new  = level, tag_type, tag_name, tag_start, attr_end + 1, attr_start, attr_end
				# We may want to write the found tag to the write stream
				if write != None:
					# We skip closing tags when writing
					if last and new and last[1] == HTML_OPEN \
					and new[1] == HTML_CLOSE and last[0] == new[0] \
					and last[2] == new[2]:
						pass
					else:
						tag_class = RE_HTMLCLASS.search(html[attr_start:attr_end])
						tag_id    = RE_HTMLID.search(html[attr_start:attr_end])
						tag_href  = RE_HTMLHREF.search(html[attr_start:attr_end])
						meta      = []
						if tag_id:    meta.append("#" + tag_id.group(1))
						if tag_class: meta.append("." + tag_class.group(1))
						if tag_href:  meta.append("<" + tag_href.group(1) + ">")
						meta = ", ".join(meta)
						if meta: meta = ": " + meta
						write.write("%-3d %s%s%s\n" % (level, "| " * level, tag_name, meta))
				yield new
				last = new
				# We may close the parent if we are in a closeOn section
				if sequence == closeOn:
					level -= 1
					parents.pop()
				# We increment the level if necessary
				if tag_name_lower in self.LEVEL_ACCOUNT:
					if tag_type == HTML_OPEN:
						parents.append(tag_name_lower)
						level += 1
				offset = tag_end_offset

	def join( self, html, tags ):
		res = []
		for tag in tags:
			if type(tag) not in (list, tuple):
				res.append(tag)
			else:
				res.append(html[tag[START]:tag[END]])
		return "".join(res)

	def cut( self, html, level=None, tags=None, text=True, method=KEEP_ABOVE ):
		last_level = 0
		parents    = []
		if tags: tags = map(string.lower, tags)
		for tag in self.iterate(html):
			if type(tag) not in (list, tuple):
				if level != None:
					if last_level + 1 == level and method.find(KEEP_SAME)==-1: continue
					if last_level + 1 <  level and method.find(KEEP_BELOW)==-1: continue
					if last_level + 1 >  level and method.find(KEEP_ABOVE)==-1: continue
				if tags and not filter(lambda t:t in parents, tags): continue
				if text: yield tag
			else:
				# We set the parents right
				while len(parents) != tag[LEVEL]: parents.pop()
				if tag[TYPE] != HTML_CLOSE: parents.append(tag[NAME].lower())
				last_level = tag[LEVEL]
				if level != None:
					if tag[LEVEL] == level and method.find(KEEP_SAME)==-1: continue
					if tag[LEVEL] <  level and method.find(KEEP_BELOW)==-1: continue
					if tag[LEVEL] >  level and method.find(KEEP_ABOVE)==-1: continue
				if tags and not filter(lambda t:t in parents, tags): continue
				yield tag

	def split( self, html, level=None, strip=None, tagOnly=False, contentOnly=False, tags=None ):
		"""Splits the given html according to the given tag. For instance,
		slicing an html document according to divs will return a list of blocks of
		text beginning and ending with divs (excepted the leading and trailing
		blocks)."""
		assert not tagOnly == contentOnly == True
		off       = 0
		cut_level = level
		for tag in self.iterate(html):
			if not type(tag) in (tuple, list): continue
			if tags != None and not tag[NAME].lower() in tags: continue
			if cut_level != None and tag[LEVEL] != cut_level: continue
			if cut_level == None: cut_level = tag[LEVEL]
			if tag[TYPE] == HTML_OPEN:
				if contentOnly: cut_off = tag[END]
				else:           cut_off = tag[START]
			else:
				if contentOnly: cut_off = tag[START]
				else: cut_off = tag[END]
			if strip and tag[TYPE] == HTML_OPEN:
				pass
			elif tagOnly:
				if tag[TYPE] != HTML_CLOSE:
					yield html[tag[START]:tag[END]]
			else:
				yield html[off:cut_off]
			off = cut_off
		if not strip and not tagOnly:
			yield html[off:]

	def levelof( self, html, tags ):
		"""Return the level where first one of the given tags is
		encountered."""
		if type(tags) in (str, unicode): tag = (tags,)
		for tag in self.iterate(html):
			if not type(tag) in (tuple, list): continue
			if tag[NAME].lower() in tags: return tag[LEVEL]
		return None

	def levels( self, html, tags ):
		"""Return the levels at which the given tags can be
		encountered."""
		if type(tags) in (str, unicode): tag = (tags,)
		levels = []
		for tag in self.iterate(html):
			if not type(tag) in (tuple, list): continue
			if tag[NAME].lower() in tags and tag[LEVEL] not in levels:
				levels.append(tag[LEVEL])
		levels.sort()
		return levels

	def text( self, data, expand=False, norm=False ):
		"""Strips the text or list (resulting from an @iterate) from HTML
		tags, so that only the text remains."""
		if type(data) in (tuple, list):
			res = "".join([text for text in data if type(text) not in (list,tuple)])
		else:
			res = "".join([text for text in self.iterate(data) if type(text) not in (list, tuple)])
		if expand: res = self.expand(res)
		if norm: res = self.norm(res)
		return res
	
	def expand( self, text ):
		"""Expands the entities found in the given text."""
		# NOTE: This is based on
		# <http://www.shearersoftware.com/software/developers/htmlfilter/>
		entityStart = text.find('&')
		if entityStart != -1:          # only run bulk of code if there are entities present
			preferUnicodeToISO8859 = 1 #(outputEncoding is not 'iso-8859-1')
			prevOffset = 0
			textParts = []
			while entityStart != -1:
				textParts.append(text[prevOffset:entityStart])
				entityEnd = text.find(';', entityStart+1)
				if entityEnd == -1:
					entityEnd = entityStart
					entity = '&'
				else:
					entity = text[entityStart:entityEnd+1]
					if len(entity) < 4 or entity[1] != '#':
						entity = htmlentitydefs.entitydefs.get(entity[1:-1],entity)
					if len(entity) == 1:
						if preferUnicodeToISO8859 and ord(entity) > 127 and hasattr(entity, 'decode'):
							entity = entity.decode('iso-8859-1')
					else:
						if len(entity) >= 4 and entity[1] == '#':
							if entity[2] in ('X','x'):
								entityCode = int(entity[3:-1], 16)
							else:
								entityCode = int(entity[2:-1])
							if entityCode > 255:
								entity = unichr(entityCode)
							else:
								entity = chr(entityCode)
								if preferUnicodeToISO8859 and hasattr(entity, 'decode'):
									entity = entity.decode('iso-8859-1')
					textParts.append(entity)
				prevOffset = entityEnd+1
				entityStart = text.find('&', prevOffset)
			textParts.append(text[prevOffset:])
			text = ''.join(textParts)
		return text

	def tree( self, html ):
		"""Creates a tree of Nodes from the given HTML document."""
		root       = Node(name=Node.ROOT,children=[], indice=-1)
		parents    = [root]
		counter    = 0
		for tag in self.iterate(html):
			#  We create the node
			if not type(tag) in (tuple, list):
				parents[-1].append(Node(name=Node.TEXT, text=tag, indice=counter))
				counter += 1
			else:
				# We pop the parents to match the level
				while len(parents) - 1 > tag[LEVEL]: parents.pop()
				# We skip close nodes
				if tag[TYPE] == HTML_CLOSE: continue
				# We create the node
				attributes = HTML.parseAttributes(html[tag[ASTART]:tag[AEND]])
				node       = Node(name=tag[NAME], attributes=attributes, indice=counter)
				counter   += 1
				# If it is single
				if tag[TYPE] == HTML_SINGLE:
					parents[-1].append(node)
				# If it is open
				else:
					parents[-1].append(node)
					parents.append(node)
		return root
	
	@staticmethod
	def norm( text ):
		return RE_SPACES.sub(" ", text).strip()

	@staticmethod
	def parseTag( text ):
		text  = text.strip()
		space = text.find(" ")
		if   text[0:2] == "</":  start = 2
		elif text[0]   == "<":   start = 1
		else:                    start = 0
		if   text[-2:0] == "/>": end    = -2
		elif text[-1]   == ">":  end   = -1
		else:                    end   = len(text)
		if space:
			name  = text[start:space]
			attr  = text[space:end].strip()
			return (name, HTML.parseAttributes(attr))
		else:
			return (text[start:end].strip(), {})

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
				return HTML.parseAttributes(text[space+1:], attribs)
		else:
			sep = text[eq+1]
			if   sep == "'": end = text.find( "'", eq + 2 )
			elif sep == '"': end = text.find( '"', eq + 2 )
			else: end = text.find(" ", eq)
			# Did we reach the end ?
			name = text[:eq].strip()
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


# We create a shared instance with the scraping tools
HTML = HTMLTools()

def do( f, *args, **kwargs ):
	"""This function is useful to "do" iterator functions which are only run if
	put within a loop or tuple/list function."""
	return tuple(f(*args, **kwargs))

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

# TODO: Add STRICT mode for form that checks possible values/action/field names

	def __init__( self, name, action=None ):
		self.name   = name
		self.action = action
		self.inputs = []
		self.values = {}

	def fields( self, namesOnly=False ):
		"""Returns that list of inputs (or input names if namesOnly is True) that
		can be assigned a value (checkboxes, inputs, text areas, etc)."""
		res = filter(lambda f:f.get("type") != "submit", self.inputs)
		if namesOnly: res = tuple(f.get("name") for f in res)
		return res

	def actions( self, namesOnly=False ):
		"""Returns the list of inputs (or input names if namesOnly is True) that
		correspond to form action buttons."""
		res = filter(lambda f:f.get("type")=="submit", self.inputs)
		if namesOnly: res = tuple(f.get("name") for f in res)
		return res

	def clear( self ):
		"""Clears the existing values set in this form, and returns them."""
		old_values = self.values
		self.values = {}
		return old_values

	def fill( self, **values ):
		"""Fills this form with the given values."""
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

	def submit( self, action=None, encoding="latin-1", strip=True, **values ):
		"""Submits this form with the given action and given values."""
		self.fill(**values)
		parameters  = []
		# We get the field and action names
		field_names  = self.fields(namesOnly=True)
		# We fill values that were initialized
		for key in field_names:
			value = self.values.get(key)
			if strip and not value: continue
			if type(value) == unicode: value = unicode(value).encode(encoding)
			if self.values.has_key(key):
				parameters.append((key, value))
		# And add values that do not correspond to any field
		for key, value in values.items():
			if key not in field_names:
				if strip and not value: continue
				if type(value) == unicode: value = unicode(value).encode(encoding)
				parameters.append((key, value))
		if action:
			if action not in self.actions(namesOnly=True):
				raise FormException("Action not available: %s, in form %s" %
				(action, self.name))
			parameters.append((action, self.values.get(action)))
		return parameters

	def _prefill( self ):
		"""Sets the default values for this form."""
		for inp in self.inputs:
			name  = inp.get("name")
			value = inp.get("value")
			if name and value: self.values[name] = value
	
	def asText( self ):
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
		return "Form '%s'->%s: %s" % (self.name, self.action, repr(self.inputs))

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
				# FIXME: Adda a warnings interface
				#if js:
				#	print "Warning: Form may contain JavaScript: ", current_form.name, "input", attributes.get("name"), js
				current_form.inputs.append(attributes)
			else:
				raise Exception("Unexpected tag: " + name)
		# Prefills the forms
		for form in forms.values():
			form._prefill()
		return forms

	def links( self, html ):
		"""Iterates through the links found in this document. This yields the
		tag name and the href value."""
		if not html: raise ScraperException("No data: " + repr(html))
		for match in self.onRE(html, RE_HTMLLINK):
			tag  = match.group()
			tag  = tag[1:tag.find(" ")]
			href = match.group(2)
			if href[0] in ("'", '"'): href = href[1:-1]
			yield tag, href

	@staticmethod
	def onRE( text, regexp, off=0 ):
		"""Itearates through the matches for the given regular expression."""
		res = True
		while res:
			res = regexp.search(text, off)
			if res:
				off = res.end()
				yield res

# The default scraper
scraper = Scraper()

# EOF
