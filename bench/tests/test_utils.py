# imports - compatibility imports
from builtins import FileExistsError

# imports - standard imports
import os, shutil
import os.path as osp

# imports - third-party imports
import pytest

# imports - module imports
from bench import utils

@pytest.fixture
def tempdir():
	tempdirs = osp.join('foo', 'bar')
	yield tempdirs
	shutil.rmtree('foo')

def test_makedirs(tempdir):
	utils.makedirs(tempdir, exists_ok = True)
	assert osp.exists(tempdir)

	# In Py2, raises OSError
	with pytest.raises(FileExistsError):
		utils.makedirs(tempdir)

def test_assign_if_empty():
	assert utils.assign_if_empty('foo', 'bar') == 'foo'
	assert utils.assign_if_empty(False, 'bar') == 'bar'