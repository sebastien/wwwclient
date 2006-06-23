#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
from os.path import join, basename, dirname, abspath
import sys ;sys.path.append(join(dirname(dirname(abspath(__file__))), "Sources"))
import time

from wwwclient import browse, scrape


scraper = scrape.Scraper()
session = browse.Session()
session.get("http://ppg.hebdo.net/login.aspx")

login_form = scraper.forms(session.last().data()).values()[0]
session.submit( login_form,
	values={"frmUserName":"gildo", "frmPassword":"gioia", "btnLogin.x":40, "btnLogin.y":40}
)

# And now we list the inventory
html       = session.get("http://ppg.hebdo.net/inventory/list.asp").data()
#print tuple(scrape.HTML.iterate(html, write=sys.stdout))
trs        = list(scrape.HTML.split(html, level=9, strip=True, tags="tr"))
for tr in trs:
	un_nbsp = lambda s:s.replace("&nbsp;", "").replace("&nbsp", "").replace("nbsp","")
	tds = map(un_nbsp, map(scrape.HTML.text, list(scrape.HTML.split(tr, strip=True, contentOnly=True, tags="td"))))
	if len(tds) != 13: continue
	print tds

# EOF
