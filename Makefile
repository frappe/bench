VIRTUALENV ?= virtualenv

VENV       := .venv
VENVBIN    ?= $(VENV)/py3/bin

PYTHON     ?= $(VENVBIN)/python
PIP        ?= $(VENVBIN)/pip

BASEDIR     = $(realpath .)
PACKAGE     = bench
SOURCEDIR   = $(realpath $(PACKAGE))

venv2:
	$(VIRTUALENV) $(VENV)/py2 --python python2

venv3:
	$(VIRTUALENV) $(VENV)/py3 --python python3

clean.py:
	find $(SOURCEDIR) | grep -E "__pycache__|.pyc" | xargs rm -rf

	rm -rf $(PACKAGE).egg-info

clean:
	make clean.py

	clear
	
install:
	cat requirements/*.txt 			> requirements-dev.txt
	cat requirements/production.txt > requirements.txt

	$(PIP) install -r requirements-dev.txt

	$(PYTHON) setup.py install

	make clean

test:
	$(PYTHON) -m bench.tests.test_setup_production

	make clean