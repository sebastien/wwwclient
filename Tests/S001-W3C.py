import _import
from wwwclient import browse, scrape

__doc__ = """
Retrieves the list of HTML elements from the W3 spec pages and formats it as a
CSV file.
"""

HTML = scrape.HTML
session = browse.Session()
session.verbose = True
session.get("http://www.w3.org/TR/REC-html40/index/elements.html")

page   = HTML.parse(session.last().data())
titles = None
trs    = page.elements(withName='tr')
titles = map(lambda e:e.get("title"), trs[1].elements(withName='td'))
print "# W3C HTML ELEMENTS INDEX"
print ";".join(titles)
for tr in page.elements(withName='tr')[1:]:
	for td in tr.elements(withName='td'):
		title = td.get("title")
		print HTML.text(td.innerhtml(),expand=True,norm=True) + ";",
	print

print "OK"


