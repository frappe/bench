from setuptools import setup, find_packages
from pip.req import parse_requirements
import re
import ast

# get version from __version__ variable in bench/__init__.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('bench/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

requirements = parse_requirements("requirements.txt", session="")

setup(
	name='bench',
	description='Metadata driven, full-stack web framework',
	author='Frappe Technologies',
	author_email='info@frappe.io',
	version=version,
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=[str(ir.req) for ir in requirements],
	dependency_links=[str(ir._link) for ir in requirements if ir._link],
	entry_points='''
[console_scripts]
bench=bench.cli:cli
''',
)
