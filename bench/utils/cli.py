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
			raise TypeError("Command has no name.")
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

def generate_file_hash(file):
	from hashlib import md5
	data_chunk = 65535 #64 kB
	md5_hash = md5()
	
	with open(file,'rb') as f:
		while True:
			data = f.read(data_chunk)
			if not data:
				break
			md5_hash.update(data)
	
	return md5_hash.hexdigest()

def files_in_directory(directory_path) -> list:
	from os import walk
	path_list = []
	for base_path, subdirectory, file_names in walk(directory_path):
		for file_name in file_names:
			path_list.append(base_path + "/" + file_name)
	return path_list

def get_files_data(list_of_config_files):
	from os.path import getmtime
	for file in list_of_config_files:
		file_hash = generate_file_hash(file)
		modified_time = getmtime(file)
		yield file, file_hash, modified_time

def add_to_config_log_file(json_obj, bench_path):
	with open(bench_path + "/.bench_configs.json", "w") as f:
		f.write(json_obj)

def log_config_json(bench_path="."):
	from bench.utils import is_bench_directory, log
	from json import dumps as write_json
	if not is_bench_directory(bench_path):
		log("ERROR: Could not log config files", level=2)
		return
	config_files = files_in_directory(bench_path+"/config")
	config_files_data_json = {}
	for file_path, hash, mtime in get_files_data(config_files):
		config_files_data_json[file_path] = {"hash": hash, "modified_time": mtime}
	
	add_to_config_log_file(write_json(config_files_data_json, indent = 2), bench_path)
	log("Latest configuration has been applied", level = 1)

def is_config_changed(bench_path="."):
	from bench.utils import is_bench_directory, log
	from json import load as read_json
	if not is_bench_directory(bench_path):
		log("Run the command from bench directory to check config changes", level = 3)
	saved_config_data = {}
	current_config_data = {}
	config_files = files_in_directory(bench_path+"/config")
	for file_path, hash, mtime in get_files_data(config_files):
		current_config_data[file_path] = {"hash": hash, "modified_time": mtime}
	with open(bench_path + "/.bench_configs.json", 'r') as f:
		saved_config_data = read_json(f)

	if saved_config_data != current_config_data:
		return True
	else:
		return False