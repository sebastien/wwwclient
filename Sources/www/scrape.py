import re

RE_SPACES   = re.compile("\s+")
RE_FORMDATA = re.compile("<(form|input)", re.I)

class Form:
	"""A simple interface to forms, returned by the scraper. Forms can be easily
	filled and their values (@values) can be given as parameters to the @browse
	module."""

	def __init__( self, name, action=None ):
		self.name   = name
		self.action = action
		self.inputs = []
		self.values = {}

	def fields( self ):
		return filter(lambda f:f, map(lambda i:i.get("name"), self.inputs))
	
	def action( self ):
		actions = filter(lambda f:f, map(lambda i:i.get("name"), self.inputs))
	def prefill( self ):
		for inp in self.inputs:
			name  = inp.get("name")
			value = inp.get("value")
			if name and value: self.values[name] = value
	
	def fill( self, **values ):
		fields = self.fields()
		for name, value in values.items():
			if not name in fields:
				print "Unexpected value:", name,"=",value
			else:
				self.values[name] = value
	
	def submit( self, session, **values ):
		self.prefill()
		self.fill(**values)

	def __repr__( self ):
		return repr(self.inputs)

class Scraper:
	
	def forms( self, html ):
		i       = 0
		end     = len(html)
		matches = []
		# We get all the form data
		while i < end:
			match = RE_FORMDATA.search(html, i)
			if not match: break
			matches.append(match)
			i = match.end()
		def parse_attribute(text, attribs = None):
			if attribs == None: attribs = {}
			eq = text.find("=")
			if eq == -1: return attribs
			sep = text[eq+1]
			if   sep == "'": end = text.find( "'", eq + 2 )
			elif sep == '"': end = text.find( '"', eq + 2 )
			else: end = text.find(" ", eq)
			if end == -1: return attribs
			name = text[:eq]
			value = text[eq+1:end+1]
			if value[0] in ("'", '"'): value = value[1:-1]
			attribs[name.lower()] = value
			return parse_attribute(text[end+1:].strip(), attribs)
		# And we create the forms tree
		current_form = None
		forms        = {}
		for match in matches:
			tag_end    = html.find(">", match.end())
			name       = match.group(1).lower()
			attributes = parse_attribute(html[match.end():tag_end].strip())
			if name == "form":
				# TODO: Ensure name attribute
				current_form = Form(attributes["name"], attributes.get("action"))
				forms[current_form.name] = current_form
			elif name == "input":
				assert current_form
				# TODO: Make this nicer
				if filter(lambda s:s.startswith("on"), attributes.keys()):
					print "Warning: Form may contain JavaScript: ", current_form.name, "in input", attributes
				current_form.inputs.append(attributes)
			else:
				raise Exception("Unexpected tag: " + name)
		return forms

# EOF
