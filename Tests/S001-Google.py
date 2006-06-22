#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
from os.path import join, basename, dirname, abspath
import sys ; sys.path.append(join(dirname(dirname(abspath(__file__))), "Sources"))

from wwwclient import browse, scrape

scraper = scrape.Scraper()
session = browse.Session()
session.verbose = True
session.get("www.google.com/")

search_form = scraper.forms(session.last().data()).values()[0]
session.submit( search_form, values={"q":"Britney Spears"}, action="btnG",
method=browse.GET ).data()

# Google results are not properly closed, so we had to identify patterns where
# there were  a closing tag should be inserted
close_on = ("td", "a", "img", "br", "a")
scrape.do(scrape.HTML.iterate, session.last().data(), closeOn=close_on, write=sys.stdout)
# EOF
