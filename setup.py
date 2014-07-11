from setuptools import setup, find_packages

setup(
    name='bench',
    version='0.1',
    py_modules=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'jinja2',
    ],
    entry_points='''
[console_scripts]
bench=bench.cli:bench
''',
)
