from   wwwclient import Session, quote
import string
data={}
for browser in "Firefox,Safari,Chrome,Internet Explorer".split(","):
	data[browser]={}
	div = Session(verbose=1).get("http://www.useragentstring.com/pages/%s/" % (quote(browser))).query("#liste")[0]
	version = None
	for _ in div.children:
		if _.hasName("h4"):
			version = _.text().split()[-1]
			if version[0] not in string.digits:
				version = None
		elif _.hasName("ul"):
			if version:
				data[browser][version] = map(lambda _:_.text(), _.query("li a"))
import json
print "DATA=",json.dumps(data,indent=True)
# EOF
