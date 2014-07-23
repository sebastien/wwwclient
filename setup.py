#!/usr/bin/python
# Encoding: ISO-8859-1
# -----------------------------------------------------------------------------
# Project   : WWWClient
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                      <sebastien.piere@gmail.com>
# -----------------------------------------------------------------------------
# License   : GNU Lesser General Public License
# Credits   : Xprima.com
# -----------------------------------------------------------------------------
# Creation  : 26-Jul-2006
# Last mod  : 23-Jul-2014
# -----------------------------------------------------------------------------

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

PROJECT     = "wwwclient"
LICENSE     = "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)"
VERSION = eval(filter(lambda _:_.startswith("__version__"), file("Sources/wwwclient/__init__.py").readlines())[0].split("=")[1])
SUMMARY     = "Advanced Web Browsing, Scraping And Automation"
DESCRIPTION = """\
WWWClient is a web browsing, scraping and automation client and library that can
easily be used using an interpreter (like 'ipython') or embedded within a
program. WWWClient offers both a high-level API and fine-grain control over
low-level HTTP and web specific elements, as well as a powerful scraping API
that lets you manipulate your HTML document using string, list and tree
operations at the same time.
"""
KEYWORDS    = "web browing, web client, scraping, forms, http client, curl"

# ------------------------------------------------------------------------------
#
# SETUP DECLARATION
#
# ------------------------------------------------------------------------------

setup(
    name        = PROJECT,
    version     = VERSION,
    author      = "Sebastien Pierre", author_email = "sebastien@ivy.fr",
    description = SUMMARY,
	long_description = DESCRIPTION,
    license     = LICENSE,
    keywords    = KEYWORDS,
    url         = "http://github.com/sebastien/%s" % (PROJECT.lower()),
    download_url= "http://github.com/sebastien/%s/tarball/%s" % (PROJECT.lower(),VERSION) ,
    package_dir = { "": "Sources" },
    packages    = [PROJECT.lower()],
    classifiers = [
      # See <http://pypi.python.org/pypi?:action=list_classifiers>
      "Development Status :: 5 - Production/Stable",
      "Environment :: Web Environment",
      "Intended Audience :: Developers",
      "Intended Audience :: Information Technology",
      "Natural Language :: English",
      "Topic :: Internet :: WWW/HTTP",
      "Operating System :: POSIX",
      "Operating System :: Microsoft :: Windows",
      "Programming Language :: Python",
    ]
)
# EOF - vim: tw=80 ts=4 sw=4 noet
