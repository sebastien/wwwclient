from wwwclient import *

agents = {}
for line in Session().get("http://www.robotstxt.org/db/all.txt").data().split("\n"):
	if not line.startswith("robot-useragent"): continue
	useragent = line.split(":",1)[-1].strip()
	useragent = useragent.split("/")[0].lower()
	if useragent and useranget not in ("mozilla": agents[] = True
print agents
