"""
Collect the frappe click command tree and emit it as JSON to stdout.

Run inside the frappe virtualenv (bench's Python) so that frappe is importable.
Progress lines are written to stderr so they can be shown or suppressed
independently of the JSON output.

stdout: JSON object mapping completion-key strings to
        {"options": [...], "value_options": [...], "path_options": [...],
         "path_positionals": [...], "commands": [...]}
stderr: one line per command as it is scanned
exit 1: if the frappe click group cannot be located
"""

import json
import sys

import click
import frappe.utils.bench_helper as _bh

from completion_utils import param_expects_path

FRAPPE_KEY = "__frappe__"
MAX_DEPTH = 4


def _dedupe(values):
	return list(dict.fromkeys(values))


def _option_flags(param):
	return _dedupe([*param.opts, *(param.secondary_opts or [])])


def _scan_option(param):
	flags = _option_flags(param)
	if param.is_flag or param.nargs == 0:
		return flags, [], []

	path_flags = flags if param_expects_path(param) else []
	return flags, flags, path_flags


def _scan_options(params):
	options = []
	value_options = []
	path_options = []

	for param in params:
		if not isinstance(param, click.Option):
			continue

		flags, value_flags, path_flags = _scan_option(param)
		options.extend(flags)
		value_options.extend(value_flags)
		path_options.extend(path_flags)

	return options, value_options, path_options


def _path_positionals(params):
	path_positionals = []
	positional_index = 0

	for param in params:
		if not isinstance(param, click.Argument):
			continue
		if param_expects_path(param):
			path_positionals.append(str(positional_index))
		positional_index += 1

	return path_positionals


def _walk_children(cmd, path, depth, result):
	commands = getattr(cmd, "commands", None)
	if not commands or depth >= MAX_DEPTH:
		return []

	for name, child in commands.items():
		_walk(child, path + [name], depth + 1, result)
	return list(commands)


def _completion_spec(cmd, path, depth, result):
	options, value_options, path_options = _scan_options(cmd.params)
	child_commands = _walk_children(cmd, path, depth, result)

	return {
		"options": _dedupe(["--help", *options]),
		"value_options": _dedupe(value_options),
		"path_options": _dedupe(path_options),
		"path_positionals": _dedupe(_path_positionals(cmd.params)),
		"commands": child_commands,
	}


def _walk(cmd, path, depth, result):
	key = f"{FRAPPE_KEY} {' '.join(path)}" if path else FRAPPE_KEY
	result[key] = _completion_spec(cmd, path, depth, result)
	label = " ".join(["frappe", *path]) if path else "frappe"
	print(f"  {label}", file=sys.stderr, flush=True)


app_groups = _bh.get_app_groups()
frappe_group = app_groups.get("frappe")

if frappe_group is None or not hasattr(frappe_group, "commands"):
	print("error: frappe group not found in bench_helper", file=sys.stderr)
	sys.exit(1)

result = {}
_walk(frappe_group, [], 0, result)
print(json.dumps(result))
