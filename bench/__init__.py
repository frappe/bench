from jinja2 import Environment, PackageLoader

VERSION = "5.0.0"
PROJECT_NAME = "frappe-bench"
FRAPPE_VERSION = None
__version__ = VERSION
env = Environment(loader=PackageLoader('bench.config'))


def set_frappe_version(bench_path='.'):
	from .app import get_current_frappe_version
	global FRAPPE_VERSION
	if not FRAPPE_VERSION:
		FRAPPE_VERSION = get_current_frappe_version(bench_path=bench_path)