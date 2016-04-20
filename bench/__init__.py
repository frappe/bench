from jinja2 import Environment, PackageLoader

__version__ = "3.0.0"

env = Environment(loader=PackageLoader('bench.config'), trim_blocks=True)
