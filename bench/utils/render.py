# imports - standard imports
import sys
from io import StringIO

# imports - third party imports
import click

# imports - module imports
import bench


class Capturing(list):
	"""
	Util to consume the stdout encompassed in it and push it to a list

	with Capturing() as output:
	        subprocess.check_output("ls", shell=True)

	print(output)
	# ["b'Applications\\nDesktop\\nDocuments\\nDownloads\\n'"]
	"""

	def __enter__(self):
		self._stdout = sys.stdout
		sys.stdout = self._stringio = StringIO()
		return self

	def __exit__(self, *args):
		self.extend(self._stringio.getvalue().splitlines())
		del self._stringio  # free up some memory
		sys.stdout = self._stdout


class Rendering:
	def __init__(self, success, title, is_parent, args, kwargs):
		import bench.cli

		self.dynamic_feed = bench.cli.from_command_line and bench.cli.dynamic_feed

		if not self.dynamic_feed:
			return

		try:
			self.kw = args[0].__dict__
		except Exception:
			self.kw = kwargs

		self.is_parent = is_parent
		self.title = title
		self.success = success

	def __enter__(self, *args, **kwargs):
		if not self.dynamic_feed:
			return

		_prefix = click.style("⏼", fg="bright_yellow")
		_hierarchy = "" if self.is_parent else "  "
		self._title = self.title.format(**self.kw)
		click.secho(f"{_hierarchy}{_prefix} {self._title}")

		bench.LOG_BUFFER.append(
			{
				"message": self._title,
				"prefix": _prefix,
				"color": None,
				"is_parent": self.is_parent,
			}
		)

	def __exit__(self, *args, **kwargs):
		if not self.dynamic_feed:
			return

		self._prefix = click.style("✔", fg="green")
		self._success = self.success.format(**self.kw)

		self.render_screen()

	def render_screen(self):
		click.clear()

		for l in bench.LOG_BUFFER:
			if l["message"] == self._title:
				l["prefix"] = self._prefix
				l["message"] = self._success
			_hierarchy = "" if l.get("is_parent") else "  "
			click.secho(f'{_hierarchy}{l["prefix"]} {l["message"]}', fg=l["color"])


def job(title: str = None, success: str = None):
	"""Supposed to be wrapped around an atomic job in a given process.
	For instance, the `get-app` command consists of two jobs: `initializing bench`
	and `fetching and installing app`.
	"""

	def innfn(fn):
		def wrapper_fn(*args, **kwargs):
			with Rendering(
				success=success,
				title=title,
				is_parent=True,
				args=args,
				kwargs=kwargs,
			):
				return fn(*args, **kwargs)

		return wrapper_fn

	return innfn


def step(title: str = None, success: str = None):
	"""Supposed to be wrapped around the smallest possible atomic step in a given operation.
	For instance, `building assets` is a step in the update operation.
	"""

	def innfn(fn):
		def wrapper_fn(*args, **kwargs):
			with Rendering(
				success=success,
				title=title,
				is_parent=False,
				args=args,
				kwargs=kwargs,
			):
				return fn(*args, **kwargs)

		return wrapper_fn

	return innfn
