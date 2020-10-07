VERSION = "5.2.1"
PROJECT_NAME = "frappe-bench"
FRAPPE_VERSION = None


def set_frappe_version(bench_path='.'):
	from .app import get_current_frappe_version
	global FRAPPE_VERSION
	if not FRAPPE_VERSION:
		FRAPPE_VERSION = get_current_frappe_version(bench_path=bench_path)


def supports_color():
	"""
	Returns True if the running system's terminal supports color, and False
	otherwise.
	"""
	import sys
	plat = sys.platform
	supported_platform = plat != 'Pocket PC' and (plat != 'win32' or 'ANSICON' in os.environ)
	# isatty is not always implemented, #6223.
	is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
	return supported_platform and is_a_tty

COLORED_OUTPUT = supports_color()
