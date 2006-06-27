from os.path import join, basename, dirname, abspath
import sys ;sys.path.append(join(dirname(dirname(abspath(__file__))), "Sources"))

from wwwclient import scrape

HTML = """<table border=1 cellpadding=1 cellspacing=0 align=center bordercolor=#EEEEEE width=610><tr><td class=tdblk valign=top colspan=13><form method=post name=myform action="list.asp"><img src="/images/spacer_trans.gif" width=1 height=2></td></tr>"""

for tag in scrape.HTML.iterate(HTML):
	print tag
