#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : WWWClient - Python client Web toolkit
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre <sebastien@xprima.com>
# Creation  : 19-Jun-2006
# Last mod  : 12-Sep-2006
# -----------------------------------------------------------------------------

# TODO: The tree could be created by the iterate function, by directly linking
# nodes. So the tree could be unfolded as a list, or kept folded as a tree. This
# would allow to have still one structure. Ideally, the original HTML could be
# kept to allow easy subset extraction (currently, the data is recreated)

import re, string, htmlentitydefs
import form

__doc__ = """\
The scraping module gives a set of functionalities to manipulate HTML data. All
functions are text oriented, so that they work with any subset of an HTML
document. This is very useful, as it does not require the HTML to be
well-formed, and allows easy selection of HTML fragments."""

RE_SPACES    = re.compile("\s+")
RE_HTMLSTART = re.compile("</?(\w+)",      re.I)
RE_HTMLEND   = re.compile("/?>")
RE_HTMLLINK  = re.compile("<[^<]+(href|src)\s*=\s*('[^']*'|\"[^\"]*\"|[^ ]*)", re.I)

RE_HTMLCLASS = re.compile("class\s*=\s*['\"]?([\w\-_\d]+)", re.I)
RE_HTMLID    = re.compile("id\s*=\s*['\"]?([\w\-_\d]+)", re.I)
RE_HTMLHREF  = re.compile("href\s*=\s*('[^']*'|\"[^\"]*\"|[^ ]*)", re.I)

RE_SPACES    = re.compile("\s+", re.MULTILINE)

KEEP_ABOVE    = "+"
KEEP_SAME     = "="
KEEP_BELOW    = "-"

# -----------------------------------------------------------------------------
#
# HTML TAG INTERFACE
#
# -----------------------------------------------------------------------------

class Tag:
	"""A Tag is an abstract decorator for a portion within a string. Tags are
	used in this module to identify HTML/XML data within strings."""
	OPEN  = "open"
	CLOSE = "close"
	EMPTY = "empty"

	def __init__( self, html, start, end ):
		"""Creates a new new tag."""
		self._html  = html
		self.start  = start
		self.end    = end

	def html( self ):
		"""Returns the HTML representation of this tag."""
		return self._html[self.start:self.end]
		
	def __repr__( self ):
		return repr(self._html[self.start:self.end])

class ElementTag(Tag):

	def __init__( self, html, name, start, end, astart=None, aend=None, attributes=None,
	level=None, type=None ):
		Tag.__init__(self, html, start, end)
		if type == None: type = Tag.OPEN
		self._attributes = attributes
		self.astart      = astart
		self.aend        = aend
		self.level       = level
		self.type        = type

	def attributes( self ):
		if self._attributes == None:
			self._attributes = HTML.parseAttributes(self._html[self.astart:self.aend].strip())
		return self._attributes
	
	def has( self, name ):
		return self.attributes().has_key(name)

	def get( self, name ):
		return self.attributes().get(name)

	def name( self ):
		if self.type == Tag.OPEN or self.type == Tag.EMPTY:
			return self._html[self.start+1:self.astart].strip()
		else:
			return self._html[self.start+2:self.astart].strip()

	def nameLike( self, what ):
		"""Tells if the name is like the given string/list of string/regexp/list
		of regexpes."""
		if type(what) in (str, unicode):
			# TODO: Handle unicode
			return re.match(what, self.name(), re.I)
		if type(what) in (tuple, list):
			for w in what:
				if self.nameLike(w): return True
		else:
			return what.match(self.name(), re.I)

class TextTag(Tag):

	def __init__( self, html, start, end):
		Tag.__init__(self, html, start, end)

class TagList:

	def __init__( self, content=None ):
		"""Creates a blank TagTree. It should be populated with data using the
		`fromHTML` method."""
		if content == None: content = []
		self.content = content

	def append( self, content ):
		assert isinstance(content, Tag) 
		content.context = self
		self.content.append(content)
		return content

	def fromHTML( self, html, scraper=None ):
		"""Creates the tag list content from the given HTML data. This will
		erase the content of this tag list, replacing it by this one."""
		self.content = []
		offset    = 0
		level     = 0 
		end       = False
		last      = None
		if scraper == None: scraper = HTML
		while not end:
			tag = scraper.findNextTag(html, offset)
			# If there is no tag, it is the document
			if tag == None:
				self.append(TextTag( html, start=offset, end=len(html)))
				end = True
			else:
				tag, tag_end_offset = tag
				tag_type, tag_name, tag_start, attr_start, attr_end = tag
				tag_name_lower      = tag_name.lower()
				# There may be text inbetween
				if tag_start > offset:
					self.append(TextTag(html, start=offset,end=tag_start))
				# We process the encountered tag
				#new  = level, tag_type, tag_name, tag_start, attr_end + 1, attr_start, attr_end
				new = ElementTag( html, tag_name, tag_start, attr_end + 1, attr_start, attr_end, type=tag_type, level=level)
				self.append(new)
				last = new
				offset = tag_end_offset
		return self.content

	def tagtree( self ):
		"""Folds this list into a tree, which is returned as result."""
		root       = TagTree(id=-1)
		parents    = [root]
		counter    = 0
		tags_stack = []
		def find_opening_tag(tag, stack):
			for i in range(len(stack)-1,-1,-1):
				this_tag = stack[i]
				if this_tag.name() == tag.name() and this_tag.type == Tag.OPEN:
					return this_tag, i
			return None, -1
		# We iterate on the tags of this taglist
		for tag in self.content:
			#  We create the node
			if isinstance(tag, TextTag):
				parents[-1].append(TagTree(tag))
			else:
				if tag.type == Tag.CLOSE:
					opening_tag, level = find_opening_tag(tag, tags_stack)
					if not opening_tag:
						print "WARNING: no opening tag for ", tag
						continue
					else:
						while len(tags_stack) > level:
							stack_tag = tags_stack.pop()
							node      = parents.pop()
						assert stack_tag == opening_tag
						node.close(tag)
				else:
					if tags_stack and HTML_closeWhen( tag, tags_stack[-1] ):
						parent_tag = tags_stack.pop()
						closing_tag = ElementTag(tag._html, parent_tag.name(), tag.start, tag.start, type=Tag.CLOSE)
						parents.pop().close(tag)
					if tag.type == Tag.EMPTY or HTML_isEmpty(tag):
						node = TagTree(tag, id=counter)
						parents[-1].append(node)
						counter   += 1
					else:
						node = TagTree(tag, id=counter)
						parents[-1].append(node)
						parents.append(node)
						tags_stack.append(tag)
						counter   += 1
		root._taglist = self
		return root

	def html( self ):
		"""Converts this tags list to HTML"""
		res = []
		for tag in self.content:
			assert isinstance(tag, Tag) or isinstance(tag, Text)
			res.append(tag.html())
		return "".join(res)
	
	def innerhtml(self):
		res = []
		for tag in self.content[1:-1]:
			assert isinstance(tag, Tag) or isinstance(tag, Text)
			res.append(tag.html())
		return "".join(res)

	def __iter__( self ):
		for tag in self.content:
			yield tag
	
	def __str__( self ):
		return str(self.content)

class TagTree:
	"""A tree node wraps one or two tags and allows to structure tags as a tree.
	The tree node instance offers a nice interface to manipulate the HTML
	document as a tree."""

	TEXT  = "#text"

	def __init__( self, startTag=None, endTag=None, id=None ):
		self._parent   = None
		self._depth    = 0
		self._taglist  = None
		self.startTag  = None
		self.endTag    = None
		self.id        = id
		self.children  = []
		self.name      = None
		self.open(startTag)
		self.close(endTag)

	def has( self, name):
		if self.startTag == None: return None
		return self.startTag.has(name)

	def get( self, name):
		if self.startTag == None: return None
		return self.startTag.get(name)

	def attributes( self ):
		if self.startTag == None: return {}
		return self.startTag.attributes()

	def setParent( self, parent ):
		self._parent = parent
		self._depth  = self.parent().depth() + 1
	
	def parent( self ):
		return self._parent

	def depth( self ):
		return self._depth

	def isRoot( self ):
		return self._parent == None

	def elements( self, withName ):
		if self.startTag and isinstance(self.startTag, TextTag): return ()
		if self.startTag and self.startTag.nameLike(withName):
			return (self,)
		else:
			res = []
			for c in self.children:
				res.extend(c.elements(withName))
		return res

	def open( self, startTag):
		if startTag==None: return
		assert self.startTag == None
		assert self.endTag == None
		assert isinstance(startTag, Tag)
		self.startTag = startTag
		if isinstance(startTag, TextTag):
			self.name     = TagTree.TEXT
		else:
			self.name     = startTag.name()
		assert self.name, repr(startTag.html()) + ":" + startTag.name()
		return self

	def close( self, endTag ):
		if endTag==None: return
		assert self.endTag == None
		assert isinstance(endTag, ElementTag)
		self.endTag = endTag
		return self
	
	def append( self, node ):
		assert isinstance(node, TagTree)
		node.setParent(self)
		assert node != self
		self.children.append(node)
		self._taglist = None
		return self

	def taglist( self, contentOnly=False ):
		"""Returns a tag list from this Tree Node."""
		if self._taglist == None:
			content = []
			if self.startTag: content.append(self.startTag)
			for c in self.children: content.extend(c.taglist(contentOnly=True))
			if self.endTag: content.append(self.endTag)
			self._taglist = TagList(content=content)
		if contentOnly:
			return self._taglist.content
		else:
			return self._taglist

	def asText( self, ):
		if self.name == self.TEXT:
			return "#text:" + repr(self.startTag.html())
		else:
			if self._parent == None:
				res =  "#root\n"
			else:
				res =  self.startTag.name() 
				if self.id != None: res += "#%d" % (self.id) 
				attr  = []
				for k,v in self.attributes().items():attr.append("%s=%s" % (k,v))
				attr = ", ".join(attr)
				res += "@%d:%s\n" % (self.depth(), attr)
			for c in self.children:
				ctext = ""
				for line in c.asText().split("\n"):
					if not line: continue
					if not ctext:
						ctext  = "+-- " + line + "\n"
					else:
						ctext += "    " + line + "\n"
				res += ctext
			return res

	def __str__( self ):
		return self.asText()
	
	def __repr__( self ):
		return str(self.taglist())

	def html( self ):
		"""Converts this tags tree to HTML"""
		return self.taglist().html()
	
	def innerhtml( self ):
		return self.taglist().innerhtml()

	def __iter__( self ):
		for tag in self.taglist():
			yield tag

# -----------------------------------------------------------------------------
#
# HTML PRESETS
#
# -----------------------------------------------------------------------------

HTML_EMPTY = """\
AREA BASE BASEFONT BR COL FRAME HR IMG INPUT ISINDEX LINK META PARAM
"""[:-1].split()

HTML_MAYBE_EMPTY = """\
A P
"""[:-1].split()

def HTML_isEmpty( tag ):
	tag_name = tag.name().upper()
	if tag_name in HTML_EMPTY: return True
	if tag_name == "A" and not tag.has("href"): return True
	return False

def HTML_mayBeEmpty( tag ):
	tag_name = tag.name().upper()
	if tag_name in HTML_MAYBE_EMPTY: return True
	return False

def HTML_closeWhen( current, parent ):
	cur_name = (current.name() or "").upper()
	par_name = (parent.name() or "").upper()
	if cur_name == par_name == "TD": return True
	if cur_name == par_name == "TR": return True
	if cur_name == par_name == "P": return True
	if par_name == "P" and cur_name in ("DIV", "TABLE", "UL", "BLOCKQUOTE",
	"FORM"): return True
	return False

# -----------------------------------------------------------------------------
#
# HTML PARSING FUNCTIONS
#
# -----------------------------------------------------------------------------

class HTMLTools:
	"""This class contains a set of tools to process HTML text data easily. This
	class can operate on a full HTML document, or on any subset of the
	document."""

	LEVEL_ACCOUNT = [ "html", "head", "body", "div", "table", "tr", "td" ]

	def __init__( self ):
		pass

	# BASIC PARSING OPERATIONS
	# ========================================================================

	def parse( self, html ):
		"""Returns a tagtree from the given HTML string, tag list or tree
		node."""
		tag_list = TagList()
		tag_list.fromHTML(html, scraper=self)
		return tag_list.tagtree()

	def taglist( self, data ):
		"""Converts the given text or tagtree into a taglist."""
		if type(data) == str:
			tag_list = TagList()
			tag_list.fromHTML(data, scraper=self)
			return tag_list
		elif isinstance(data, TagList):
			return data
		elif isinstance(data, TagTree):
			return data.taglist()
		else:
			raise Exception("Unsupported data:" + data)

	def html( self, data ):
		"""Converts the given taglist or tagtree into HTML.""" 
		if type(data) == str:
			return data
		elif isinstance(data, TagList):
			return data.html()
		elif isinstance(data, TagTree):
			return data.html()
		else:
			raise Exception("Unsupported data:" + data)

	# TEXT OPERATIONS
	# ========================================================================

	def textcut( self, text, cutfrom=None, cutto=None ):
		"""Cuts the text from the given marker, to the given marker."""
		if cutfrom: start = text.find(cutfrom)
		else: start = 0
		if cutto: end = text.find(cutto)
		else: end = -1
		if start == -1: start = 0
		elif cutfrom: start += len(cutfrom)
		return text[start:end]

	def textlines( self, text, strip=True, empty=False ):
		"""Returns a list of lines for the given HTML text. Lines are stripped
		and empty lines are filtered out by default."""
		lines = text.split("\n")
		if strip: lines = map(string.strip, lines)
		if not empty: lines = filter(lambda x:x, lines)
		return lines

	def text( self, data, expand=False, norm=False ):
		"""Strips the given text from HTML text"""
		res = []
		for tag in self.taglist(data):
			if not isinstance(tag, TextTag): continue
			res.append(tag.html())
		res = "".join(res)
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


	# FORMS-RELATED OPERATIONS
	# ========================================================================

	def forms( self, html ):
		return form.parseForms(self, self.html(html))

	def links( self, html, like=None ):
		"""Iterates through the links found in this document. This yields the
		tag name and the href value."""
		if not html: raise Exception("No data: " + repr(html))
		if like != None:
			if type(like) in (str,unicode): like = re.compile(like)
		for match in self.onRE(html, RE_HTMLLINK):
			tag  = match.group()
			tag  = tag[1:tag.find(" ")]
			href = match.group(2)
			if href[0] in ("'", '"'): href = href[1:-1]
			if not like or like.match(href):
				yield tag, href

	# UTILITIES
	# ========================================================================

	def findNextTag( self, html, offset=0 ):
		"""Finds the next tag in the given HTML text from the given offset. This
		returns (tag type, tag name, tag start, attributes start, attributes
		end) and tag end or None."""
		if offset >= len(html) - 1: return None
		m = RE_HTMLSTART.search(html, offset)
		if m == None:
			return None
		n = RE_HTMLEND.search(html, m.end())
		if n == None:
			return HTMLTools.findNextTag(html, m.end())
		if m.group()[1] == "/": tag_type = Tag.CLOSE
		elif n.group()[0] == "/": tag_type = Tag.EMPTY
		else: tag_type = Tag.OPEN
		return (tag_type, m.group(1), m.start(), m.end(), n.start()), n.end()

	@staticmethod
	def onRE( text, regexp, off=0 ):
		"""Itearates through the matches for the given regular expression."""
		res = True
		while res:
			res = regexp.search(text, off)
			if res:
				off = res.end()
				yield res

	@staticmethod
	def norm( text ):
		"""Normalizes the spaces (\t, \n, etc) so that everything gets converted
		to single space."""
		return RE_SPACES.sub(" ", text).strip()

	@staticmethod
	def parseTag( text ):
		"""Parses the HTML/XML tag in the given text, returning its name and
		attributes."""
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
		"""Parses the HTML/XML attributes described in the given text."""
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

# EOF
