import click
from click.core import _check_multicommand


def print_bench_version(ctx, param, value):
	"""Prints current bench version"""
	if not value or ctx.resilient_parsing:
		return

	import bench
	click.echo(bench.VERSION)
	ctx.exit()


class MultiCommandGroup(click.Group):
	def add_command(self, cmd, name=None):
		"""Registers another :class:`Command` with this group.  If the name
		is not provided, the name of the command is used.

		Note: This is a custom Group that allows passing a list of names for
		the command name.
		"""
		name = name or cmd.name
		if name is None:
			raise TypeError('Command has no name.')
		_check_multicommand(self, name, cmd, register=True)

		try:
			self.commands[name] = cmd
		except TypeError:
			if isinstance(name, list):
				for _name in name:
					self.commands[_name] = cmd


def use_experimental_feature(ctx, param, value):
	if not value:
		return
	if value == "dynamic-feed":
		import bench.cli
		bench.cli.dynamic_feed = True
	else:
		from bench.exceptions import FeatureDoesNotExistError
		raise FeatureDoesNotExistError(f"Feature {value} does not exist")
