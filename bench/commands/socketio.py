# imports - standard imports
import os
import subprocess

# imports - third party imports
import click


def _python_backend_supported(python: str) -> bool:
	"""Check the frappe env actually ships the python realtime server.

	Probes with the frappe venv interpreter (not bench's) and uses find_spec
	so the module's heavy import side-effects (gevent monkey-patching) don't run.
	"""
	if not os.path.exists(python):
		return False
	try:
		return (
			subprocess.run(
				[
					python,
					"-c",
					"import importlib.util, sys;"
					"sys.exit(0 if importlib.util.find_spec('frappe.realtime.server') else 1)",
				],
				timeout=30,
			).returncode
			== 0
		)
	except (subprocess.SubprocessError, OSError):
		return False


@click.command(
	"socketio",
	help=(
		"Run the realtime (socketio) server. The backend is selected at runtime"
		" from the 'socketio_backend' key in common_site_config.json"
		" ('node' (default) or 'python'), so the process-manager command never"
		" needs to change when you switch backends."
	),
)
def socketio():
	from bench.config.common_site_config import get_config
	from bench.utils import which

	backend = (get_config(".") or {}).get("socketio_backend", "node")

	if backend not in ("node", "python"):
		click.secho(
			f"Unknown socketio_backend {backend!r}; falling back to 'node'.",
			fg="yellow",
		)
		backend = "node"

	if backend == "python":
		python = os.path.abspath(os.path.join("env", "bin", "python"))
		if _python_backend_supported(python):
			# replace this process so the manager (supervisor/systemd/honcho)
			# tracks the real server pid
			os.execv(python, [python, "-m", "frappe.realtime.server"])
		click.secho(
			"socketio_backend is 'python' but this frappe env has no"
			" 'frappe.realtime.server'; falling back to the node backend.",
			fg="yellow",
		)

	node = which("node") or which("nodejs")
	if not node:
		raise click.ClickException(
			"Cannot start socketio: node not found and the python backend is"
			" unavailable. Install node or a frappe version with"
			" frappe.realtime.server."
		)
	os.execv(node, [node, os.path.join("apps", "frappe", "socketio.js")])
