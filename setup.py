import ast
import os
import re

from setuptools import find_packages, setup

playbooks_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk("playbooks") for f in filenames]

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

with open('bench/__init__.py', 'rb') as f:
	_version_re = re.compile(r'__version__\s+=\s+(.*)')
	version = str(ast.literal_eval(_version_re.search(
		f.read().decode('utf-8')).group(1)))

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
	package_data={ 'bench': playbooks_files },
	entry_points='''
[console_scripts]
bench=bench.cli:cli
''',
)
