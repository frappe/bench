from setuptools import setup, find_packages
import re, ast

# get version from __version__ variable in bench/__init__.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

with open('bench/__init__.py', 'rb') as f:
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
	entry_points='''
[console_scripts]
bench=bench.cli:cli
''',
)
