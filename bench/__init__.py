from bench.utils import install_checker
from jinja2 import Environment, PackageLoader

__version__ = "4.1.0"

env = Environment(loader=PackageLoader('bench.config'))
install_checker()