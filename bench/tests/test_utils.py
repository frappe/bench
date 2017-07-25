import os
import shutil
import unittest

from bench.utils import is_valid_python_name, get_env_names, setup_env
import six


# adapted from: https://stackoverflow.com/a/2656405/806374 to be python 3
# compatible
def onerror(func, path, exc_info):
	"""
	Error handler for ``shutil.rmtree``.

	If the error is due to an access error (read only file)
	it attempts to add write permission and then retries.

	If the error is for another reason it re-raises the error.

	Usage : ``shutil.rmtree(path, onerror=onerror)``
	"""
	import stat
	if not os.access(path, os.W_OK):
		# Is the error an access error ?
		os.chmod(path, stat.S_IWUSR)
		func(path)
	else:
		six.reraise(exc_info)


class TestUtils(unittest.TestCase):
	def tearDown(self):
		if os.path.exists('env'):
			shutil.rmtree('env', onerror=onerror)
		if os.path.exists('env3'):
			shutil.rmtree('env3', onerror=onerror)

	def test_is_valid_python_name(self):
		self.assertEqual(is_valid_python_name('python2'), True)
		self.assertEqual(is_valid_python_name('python3'), True)
		self.assertEqual(is_valid_python_name(''), False)
		self.assertEqual(is_valid_python_name(True), False)
		self.assertEqual(is_valid_python_name(False), False)
		self.assertEqual(is_valid_python_name('test_fail'), False)

	def test_get_env_names(self):
		if not os.path.exists('env'):
			os.makedirs('env')
		self.assertEqual(sorted(get_env_names()), ['env'])

		if not os.path.exists('env3'):
			os.makedirs('env3')
		self.assertEqual(sorted(get_env_names()), ['env', 'env3'])

	def test_setup_env(self):
		with self.assertRaises(SystemExit) as test_case:
			setup_env(python_version='test_to_fail')
		self.assertEqual(test_case.exception.code, 1)

		setup_env()
		self.assertIn('env', get_env_names())

		setup_env(python_version='python3')
		self.assertIn('env3', get_env_names())
