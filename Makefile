BASEDIR = $(realpath .)

clean.py:
	find $(BASEDIR) | grep -E "__pycache__|\.pyc" | xargs rm -rf

clean:
	make clean.py

	clear