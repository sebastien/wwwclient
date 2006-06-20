#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
from os.path import join, basename, dirname, abspath
import sys ;sys.path.append(join(dirname(dirname(abspath(__file__))), "Sources"))
import time

from wwwclient import browse, scrape

scraper = scrape.Scraper()
session = browse.Session(verbose=True)
session.get("http://ppg.hebdo.net/login.aspx")
print session.last().data()

login_form = scraper.forms(session.last().data()).values()[0]
session.submit( login_form,
	values={"frmUserName":"gildo", "frmPassword":"gioia", "btnLogin.x":40, "btnLogin.y":40}
)

print "HTMl", session.last().data()
print "Cookies:", session.cookies()

#session.get("http://ppg.hebdo.net/inventory/list.asp")

# EOF
