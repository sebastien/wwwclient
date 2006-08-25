#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
from os.path import join, basename, dirname, abspath
import sys ; sys.path.append(join(dirname(dirname(abspath(__file__))), "Sources"))
from wwwclient import browse, scrape

scraper = scrape.Scraper()
session = browse.Session()
session.verbose = True
session.get('http://www.contactor.se/~dast/postit.cgi')
session.post(attach=session.attachURL("http://www.google.ca/intl/fr_ca/images/logo.gif"))
print session.last().data()

# EOF

