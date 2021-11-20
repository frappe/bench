# imports - standard imports
import sys
from io import StringIO

# imports - third party imports
import click


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


def step(title: str = None, success: str = None):
	"""Supposed to be wrapped around the smallest possible atomic step in a given operation.
	For instance, `building assets` is a step in the update operation.
	"""

	def innfn(fn):
		def wrapper_fn(*args, **kwargs):
			import bench.cli

			if bench.cli.from_command_line and bench.cli.dynamic_feed:
				kw = args[0].__dict__

				_title = f"{click.style('⏼', fg='bright_yellow')} {title.format(**kw)}"
				click.secho(_title)

			retval = fn(*args)

			if bench.cli.from_command_line and bench.cli.dynamic_feed:
				click.clear()

				for l in bench.LOG_BUFFER:
					click.secho(l["message"], fg=l["color"])

				_success = f"{click.style('✔', fg='green')} {success.format(**kw)}"
				click.echo(_success)

				bench.LOG_BUFFER.append(
					{"message": _success, "color": None,}
				)

			return retval

		return wrapper_fn

	return innfn
