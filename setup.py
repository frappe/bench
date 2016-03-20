from setuptools import setup, find_packages

setup(
	name='bench',
	description='Metadata driven, full-stack web framework',
	author='Frappe Technologies',
	author_email='info@frappe.io',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=[
		'Click',
		'jinja2',
		'virtualenv',
		'requests',
		'honcho',
		'semantic_version',
		'GitPython==0.3.2.RC1',
		'websocket'
	],
	entry_points='''
[console_scripts]
bench=bench.cli:cli
''',
)
