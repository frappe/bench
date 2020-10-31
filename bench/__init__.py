VERSION = "5.2.1"
PROJECT_NAME = "frappe-bench"
FRAPPE_VERSION = None


def set_frappe_version(bench_path='.'):
	from .app import get_current_frappe_version
	global FRAPPE_VERSION
	if not FRAPPE_VERSION:
		FRAPPE_VERSION = get_current_frappe_version(bench_path=bench_path)

def get_traceback():
	import sys
	import traceback

	exc_type, exc_value, exc_tb = sys.exc_info()
	trace_list = traceback.format_exception(exc_type, exc_value, exc_tb)
	body = "".join(str(t) for t in trace_list)

	return body
