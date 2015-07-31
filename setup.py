from setuptools import setup, find_packages

setup(
	name='bench',
	version='0.92',
	py_modules=find_packages(),
	include_package_data=True,
	url='https://github.com/frappe/bench',
	author='Web Notes Technologies Pvt. Ltd.',
	author_email='info@frappe.io',
	install_requires=[
		'Click',
		'jinja2',
		'virtualenv',
		'requests',
		'honcho',
		'semantic_version',
		'GitPython==0.3.2.RC1'
    ],
	entry_points='''
[console_scripts]
bench=bench.cli:cli
''',
)
