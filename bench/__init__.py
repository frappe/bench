VERSION = "5.0.0-dev"
PROJECT_NAME = "frappe-bench"
FRAPPE_VERSION = None
current_path = None
updated_path = None
LOG_BUFFER = []


def set_frappe_version(bench_path="."):
	from .utils.app import get_current_frappe_version

	global FRAPPE_VERSION
	if not FRAPPE_VERSION:
		FRAPPE_VERSION = get_current_frappe_version(bench_path=bench_path)
