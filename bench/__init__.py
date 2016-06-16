from jinja2 import Environment, PackageLoader

__version__ = "4.0.0-beta"

env = Environment(loader=PackageLoader('bench.config'), trim_blocks=True)

FRAPPE_VERSION = None

def set_frappe_version(bench_path='.'):
	from .app import get_current_frappe_version
	global FRAPPE_VERSION
	if not FRAPPE_VERSION:
		FRAPPE_VERSION = get_current_frappe_version(bench_path=bench_path)
