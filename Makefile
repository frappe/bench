VIRTUALENV ?= virtualenv

VENV       := .venv
VENVBIN    ?= $(VENV)/py3/bin

PYTHON     := $(VENVBIN)/python
IPYTHON    := $(VENVBIN)/ipython
PIP        := $(VENVBIN)/pip

BENCH      := $(VENVBIN)/bench

PYTEST     := $(VENVBIN)/pytest
CANIUSEPY3 := $(VENVBIN)/caniusepython3

BASEDIR    := $(realpath .)
PACKAGE    := bench
SOURCEDIR  := $(BASEDIR)/$(PACKAGE)

venv2:
	$(VIRTUALENV) $(VENV)/py2 --python python2

venv3:
	$(VIRTUALENV) $(VENV)/py3 --python python3

clean.py:
	find $(SOURCEDIR) | grep -E "__pycache__|.pyc" | xargs rm -rf

	rm -rf $(PACKAGE).egg-info $(BASEDIR)/build $(BASEDIR)/dist

clean.test:
	rm -rf $(BASEDIR)/test-bench $(BASEDIR)/test-disable-prod
	rm -rf $(BASEDIR)/.cache

clean:
	make clean.py clean.test

	clear
	
install:
	cat $(BASEDIR)/requirements/*.txt          > $(BASEDIR)/requirements-dev.txt
	cat $(BASEDIR)/requirements/production.txt > $(BASEDIR)/requirements.txt

	$(PIP) install --upgrade -r $(BASEDIR)/requirements-dev.txt

	$(PYTHON) setup.py install

	make clean

console:
	$(IPYTHON)

check.py3:
	$(CANIUSEPY3) --requirements $(BASEDIR)/requirements-dev.txt

test:
	$(PYTEST) $(SOURCEDIR)

	make clean.test clean.py