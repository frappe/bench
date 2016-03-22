from jinja2 import Environment, PackageLoader

__version__ = "2.0.0"

env = Environment(loader=PackageLoader('bench.config'), trim_blocks=True)
