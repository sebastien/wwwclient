PROJECT     = wwwclient
SOURCES     = $(wildcard Sources/$(PROJECT)/*.py)
MANIFEST    = $(SOURCES) $(wildcard Sources/*.py $(PROJECT)-api.html AUTHORS* README* LICENSE*)
VERSION     = `grep __version__ Sources/$(PROJECT)/__init__.py | cut -d '=' -f2  | xargs echo`
PRODUCT     = MANIFEST doc

.PHONY: all doc clean check
	
all: $(PRODUCT)

release: $(PRODUCT)
	git commit -a -m "Release $(VERSION)"
	git tag $(VERSION) ; true
	git push --all ; true
	python setup.py clean sdist register upload

test:
	python tests/test-all.py

clean:
	@rm -rf api/ build dist MANIFEST ; true

check:
	pychecker -100 $(SOURCES)

doc: $(DOC_SOURCES)
	sdoc -t "$(PROJECT) API"        --markup=texto $(SOURCES) $(PROJECT)-api.html

test:
	python tests/all.py

MANIFEST: $(MANIFEST)
	echo $(MANIFEST) | xargs -n1 | sort | uniq > $@

#EOF
