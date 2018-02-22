from jinja2 import Environment, PackageLoader

__version__ = "4.1.0"

env = Environment(loader=PackageLoader('bench.config'))

FRAPPE_VERSION = None

def set_frappe_version(bench_path='.'):
	from .app import get_current_frappe_version
	global FRAPPE_VERSION
	if not FRAPPE_VERSION:
		FRAPPE_VERSION = get_current_frappe_version(bench_path=bench_path)