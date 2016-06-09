from jinja2 import Environment, PackageLoader

__version__ = "4.0.0-beta"

env = Environment(loader=PackageLoader('bench.config'), trim_blocks=True)
