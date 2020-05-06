from setuptools import find_packages, setup
from bench import PROJECT_NAME, VERSION

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

setup(
	name=PROJECT_NAME,
	description='Metadata driven, full-stack web framework',
	author='Frappe Technologies',
	author_email='info@frappe.io',
	version=VERSION,
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
	entry_points='''
[console_scripts]
bench=bench.cli:cli
''',
)
