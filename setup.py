from setuptools import setup

setup(
    name='bench',
    version='0.1',
    py_modules=['bench'],
    include_package_data=True,
    install_requires=[
        'Click',
    ],
    entry_points='''
[console_scripts]
bench=bench.cli:bench
''',
)
