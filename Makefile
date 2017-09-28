PYTHON   ?= python

venv:
	virtualenv .venv/py2 --python=python2
	virtualenv .venv/py3 --python=python3

clean-py:
	python setup.py clean

clean:
	make clean-py

	clear

install:
	cat requirements/*.txt          > requirements-dev.txt
	cat requirements/production.txt > requirements.txt

	pip install -r requirements-dev.txt

	$(PYTHON) setup.py install

	make clean