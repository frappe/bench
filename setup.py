from setuptools import setup, find_packages
import re, ast
import sys

# get version from __version__ variable in bench/__init__.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('bench/__init__.py', 'rb') as f:
	version = str(ast.literal_eval(_version_re.search(
		f.read().decode('utf-8')).group(1)))

if sys.version_info[0] < 3:
	# Python 2
	install_requires_file = "install_requires_2.txt"
elif sys.version_info[0] == 3 and sys.version_info[1] <= 4:
	# Python 3.0 to 3.4
	install_requires_file = "install_requires_3.txt"
elif sys.version_info[0] == 3 and sys.version_info[1] >= 5:
	# Starting in Python 3.5, remove dependency on 'virtualenv'
	install_requires_file = "install_requires_3_5.txt"
else:
	raise Exception('Detected an unknown Python version, {}'.format(sys.version_info[0]))

with open(install_requires_file) as f:
	install_requires = f.read().strip().split('\n')

setup(
	name='bench',
	description='Metadata driven, full-stack web framework',
	author='Frappe Technologies',
	author_email='info@frappe.io',
	version=version,
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
	entry_points='''
[console_scripts]
bench=bench.cli:cli
''',
)
