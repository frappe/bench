from jinja2 import Environment, PackageLoader

env = Environment(loader=PackageLoader('bench.config'), trim_blocks=True)
