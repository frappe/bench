from typing import List
import click
from click.core import _check_nested_chain


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
			raise TypeError("Command has no name.")
		_check_nested_chain(self, name, cmd, register=True)

		try:
			self.commands[name] = cmd
		except TypeError:
			if isinstance(name, list):
				for _name in name:
					self.commands[_name] = cmd


class SugaredOption(click.Option):
	def __init__(self, *args, **kwargs):
		self.only_if_set: List = kwargs.pop("only_if_set")
		kwargs["help"] = (
			kwargs.get("help", "")
			+ f". Option is acceptable only if {', '.join(self.only_if_set)} is used."
		)
		super().__init__(*args, **kwargs)

	def handle_parse_result(self, ctx, opts, args):
		current_opt = self.name in opts
		if current_opt and self.only_if_set:
			for opt in self.only_if_set:
				if opt not in opts:
					deafaults_set = [x.default for x in ctx.command.params if x.name == opt]
					if not deafaults_set:
						raise click.UsageError(f"Illegal Usage: Set '{opt}' before '{self.name}'.")

		return super().handle_parse_result(ctx, opts, args)


def use_experimental_feature(ctx, param, value):
	if not value:
		return

	if value == "dynamic-feed":
		import bench.cli

		bench.cli.dynamic_feed = True
		bench.cli.verbose = True
	else:
		from bench.exceptions import FeatureDoesNotExistError

		raise FeatureDoesNotExistError(f"Feature {value} does not exist")

	from bench.cli import is_envvar_warn_set

	if is_envvar_warn_set:
		return

	click.secho(
		"WARNING: bench is using it's new CLI rendering engine. This behaviour has"
		f" been enabled by passing --{value} in the command. This feature is"
		" experimental and may not be implemented for all commands yet.",
		fg="yellow",
	)


def setup_verbosity(ctx, param, value):
	if not value:
		return

	import bench.cli

	bench.cli.verbose = True
