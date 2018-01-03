#!/usr/bin/env python
# vim: tw=80 ts=4 sw=4 noet
from os.path import join, basename, dirname, abspath
import _import
from wwwclient import browse, scrape
HTML = scrape.HTML

# Interestingly, there is a bug (or a trick) for the Freshmeat website, where
# the returned `Location` header is growing:
session  = browse.Session("www.freshmeat.net", follow=True)

print session.page()
page = session.page()
# 
# most_popular = page.find("MOST POPULAR PROJECTS")
# table        = page.find("<table", most_popular)
# mp_end       = page.find("<! DoubleClick", table)
# table_end    = page.rfind("</table>", mp_end)
# 
# print page[table:table:end+8]
# 


# Google results are not properly closed, so we had to identify patterns where
# there were  a closing tag should be inserted
# close_on = ("td", "a", "img", "br", "a")
# scrape.do(scrape.HTML.iterate, session.last().data(), closeOn=close_on, write=sys.stdout)
# EOF
