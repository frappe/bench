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

FRAPPE_KEY = "__frappe__"
MAX_DEPTH = 4
_PATH_NAME_HINTS = ("path", "file", "certificate", "sql", "clone_from")


def _normalize_param_name(name: str) -> str:
    return name.lower().replace("-", "_")


def _looks_like_path_name(name: str) -> bool:
    normalized = _normalize_param_name(name)
    return any(hint in normalized for hint in _PATH_NAME_HINTS)


def _param_expects_path(param) -> bool:
    if isinstance(param.type, click.Path):
        return True

    names = []
    if isinstance(param, click.Option):
        if param.name:
            names.append(param.name)
        names.extend(option.lstrip("-") for option in param.opts)
    elif isinstance(param, click.Argument) and param.name:
        names.append(param.name)

    return any(_looks_like_path_name(name) for name in names)


def _walk(cmd, path, depth, result):
    key = (FRAPPE_KEY + " " + " ".join(path)) if path else FRAPPE_KEY
    opts, vopts, path_opts, path_pos, kids = [], [], [], [], []
    positional_index = 0

    for param in cmd.params:
        if isinstance(param, click.Option):
            flags = list(dict.fromkeys([*param.opts, *(param.secondary_opts or [])]))
            opts.extend(flags)
            if not param.is_flag and param.nargs != 0:
                vopts.extend(flags)
                if _param_expects_path(param):
                    path_opts.extend(flags)
            continue

        if isinstance(param, click.Argument):
            if _param_expects_path(param):
                path_pos.append(str(positional_index))
            positional_index += 1

    if hasattr(cmd, "commands") and depth < MAX_DEPTH:
        for name, child in cmd.commands.items():
            kids.append(name)
            _walk(child, path + [name], depth + 1, result)

    result[key] = {
        "options": list(dict.fromkeys(["--help", *opts])),
        "value_options": list(dict.fromkeys(vopts)),
        "path_options": list(dict.fromkeys(path_opts)),
        "path_positionals": list(dict.fromkeys(path_pos)),
        "commands": kids,
    }

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
