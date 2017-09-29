# module  - bench
# imports - third-party imports
from jinja2 import Environment, PackageLoader

# imports - module imports
from bench.__attr__ import __version__, __release__

env = Environment(loader=PackageLoader('bench.config'))

FRAPPE_VERSION = None

def set_frappe_version(bench_path='.'):
	from .app import get_current_frappe_version
	global FRAPPE_VERSION
	if not FRAPPE_VERSION:
		FRAPPE_VERSION = get_current_frappe_version(bench_path=bench_path)
