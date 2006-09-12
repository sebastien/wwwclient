#!/usr/bin/env python
# vim: tw=80 ts=4 sw=4 noet
from os.path import join, basename, dirname, abspath
import _import
from wwwclient import browse, scrape
HTML = scrape.HTML

session  = browse.Session("www.google.com/")
page     = session.page()
forms    = HTML.forms(page)

search_form = forms["f"]
search_form.fill( q="Britney Spears" )
session.submit(search_form, action="btnG", method="GET")
page = session.page()

print page
print HTML.parse(page)

# Google results are not properly closed, so we had to identify patterns where
# there were  a closing tag should be inserted
# close_on = ("td", "a", "img", "br", "a")
# scrape.do(scrape.HTML.iterate, session.last().data(), closeOn=close_on, write=sys.stdout)
# EOF
