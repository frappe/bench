import os
import shlex
from pathlib import Path

import click

from bench.utils import find_parent_bench, get_cmd_output, get_env_frappe_commands
from bench.utils.bench import get_env_cmd


ROOT_KEY = "__root__"
FRAPPE_KEY = "__frappe__"
MAX_FRAPPE_DEPTH = 4
FORWARDED_FLAGS = ["--verbose", "-v", "--profile", "--force"]
FORWARDED_VALUE_OPTIONS = ["--site", "-s"]

# Path to the collector script that runs inside the frappe virtualenv.
# Kept as a separate file so it gets syntax highlighting, linting, and can be
# run or inspected directly without extracting it from a string constant.
_FRAPPE_SPEC_COLLECTOR = Path(__file__).parent / "frappe_spec_collector.py"


@click.command(
	"completions",
	help="Install shell completion for bench (bash or zsh).",
)
@click.option("--bash", "shell", flag_value="bash", help="Generate bash completion.")
@click.option("--zsh", "shell", flag_value="zsh", help="Generate zsh completion.")
@click.option(
	"--path",
	type=click.Path(path_type=Path, dir_okay=False, resolve_path=True),
	help="Where to write the completion script.",
)
@click.option(
	"--rc-file",
	type=click.Path(path_type=Path, dir_okay=False, resolve_path=True),
	help="Shell rc file to append the source line to.",
)
@click.option(
	"--skip-rc",
	is_flag=True,
	help="Write the completion file but do not modify shell rc files.",
)
@click.option(
	"--yes",
	"-y",
	is_flag=True,
	help="Skip the rc-file confirmation (useful in scripts or dotfile setups).",
)
def completions(shell, path, rc_file, skip_rc, yes):
	from bench.commands import bench_command

	interactive = not any([shell, path, rc_file, skip_rc, yes])

	shell = shell or _detect_shell()
	if shell not in {"bash", "zsh"}:
		raise click.UsageError("Could not detect shell. Pass --bash or --zsh.")

	path = path or _default_completion_path(shell)
	rc_file = rc_file or _default_rc_file(shell)

	if interactive:
		path = Path(
			click.prompt("Completion file", default=str(path), type=str)
		).expanduser()
		if not skip_rc:
			rc_default = str(rc_file) if rc_file else ""
			rc_response = click.prompt("Shell rc file", default=rc_default, type=str)
			rc_file = Path(rc_response).expanduser() if rc_response else None

	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		generate_completion(shell, bench_command, verbose=interactive), encoding="utf-8"
	)
	click.echo(f"Wrote completion script to {path}")

	if skip_rc:
		click.echo(f"Source it manually with: source {shlex.quote(str(path))}")
		return

	if rc_file is None:
		click.echo(f"Source it manually with: source {shlex.quote(str(path))}")
		return

	if not yes:
		should_update_rc = click.confirm(
			f"Append a source line to {rc_file}?", default=True
		)
		if not should_update_rc:
			click.echo(f"Source it manually with: source {shlex.quote(str(path))}")
			return

	loader_line = _loader_line(path)
	created = _ensure_line(rc_file, loader_line)
	if created:
		click.echo(f"Updated {rc_file}")
	else:
		click.echo(f"Loader already present in {rc_file}")

	click.echo("Open a new shell or source your rc file to activate completions.")


def generate_completion(
	shell: str, root_command: click.Command, verbose: bool = True
) -> str:
	spec = build_completion_spec(root_command, verbose=verbose)

	if shell == "bash":
		return render_bash_completion(spec)

	return render_zsh_completion(spec)


def build_completion_spec(root_command: click.Command, verbose: bool = True) -> dict:
	subcommands = {}
	options = {}
	value_options = {}

	_collect_command_tree(root_command, (), subcommands, options, value_options)

	bench_path = _find_current_bench_path()
	frappe_commands = []
	if bench_path:
		frappe_commands = _unique(get_env_frappe_commands(bench_path))
		_collect_frappe_tree(
			bench_path, subcommands, options, value_options, frappe_commands, verbose=verbose
		)

	return {
		"subcommands": subcommands,
		"options": options,
		"value_options": value_options,
		"frappe_commands": frappe_commands,
	}


def _find_current_bench_path() -> str | None:
	current_dir = os.path.abspath(".")
	return find_parent_bench(current_dir)


def _get_frappe_spec_batch(bench_path, verbose: bool = True) -> dict | None:
	import json
	import subprocess

	python = get_env_cmd("python", bench_path=bench_path)
	sites_path = os.path.join(bench_path, "sites")

	if verbose:
		click.echo("Collecting frappe completion data...", err=True)

	try:
		proc = subprocess.run(
			[python, str(_FRAPPE_SPEC_COLLECTOR)],
			cwd=sites_path,
			stdout=subprocess.PIPE,
			stderr=None if verbose else subprocess.DEVNULL,
			text=True,
		)
		if proc.returncode != 0 or not proc.stdout.strip():
			return None
		return json.loads(proc.stdout)
	except Exception:
		return None


def _collect_frappe_tree(
	bench_path, subcommands, options, value_options, fallback_commands, verbose: bool = True
):
	spec = _get_frappe_spec_batch(bench_path, verbose=verbose)

	if spec is not None:
		if FRAPPE_KEY in spec and fallback_commands:
			spec[FRAPPE_KEY]["commands"] = _unique(
				[*spec[FRAPPE_KEY]["commands"], *fallback_commands]
			)
		for key, entry in spec.items():
			subcommands[key] = entry["commands"]
			options[key] = entry["options"]
			value_options[key] = entry["value_options"]
		return

	# get_app_groups() isn't available on older frappe versions, so fall back to
	# spawning one --help subprocess per command, parallelised across each BFS level.
	_collect_frappe_tree_bfs(bench_path, subcommands, options, value_options, fallback_commands)


def _collect_frappe_tree_bfs(bench_path, subcommands, options, value_options, fallback_commands):
	from concurrent.futures import ThreadPoolExecutor, as_completed

	seen = set()
	pending = [()]

	with ThreadPoolExecutor() as executor:
		while pending:
			to_fetch = []
			for path in pending:
				key = _path_key((FRAPPE_KEY, *path))
				if key not in seen:
					seen.add(key)
					to_fetch.append(path)

			if not to_fetch:
				break

			futures = {
				executor.submit(_get_frappe_help_text, bench_path, path): path
				for path in to_fetch
			}

			next_pending = []
			for future in as_completed(futures):
				path = futures[future]
				key = _path_key((FRAPPE_KEY, *path))
				parsed = _parse_click_help(future.result())

				children = parsed["commands"]
				if not path and fallback_commands:
					children = _unique([*children, *fallback_commands])

				options[key] = _unique(["--help", *parsed["options"]])
				value_options[key] = _unique(parsed["value_options"])
				subcommands[key] = _unique(children)

				if len(path) < MAX_FRAPPE_DEPTH:
					next_pending.extend((*path, child) for child in children)

			pending = next_pending


def _get_frappe_help_text(bench_path, path) -> str:
	python = get_env_cmd("python", bench_path=bench_path)
	sites_path = os.path.join(bench_path, "sites")
	args = " ".join(shlex.quote(part) for part in path)
	cmd = f"{python} -m frappe.utils.bench_helper frappe"
	if args:
		cmd = f"{cmd} {args}"
	cmd = f"{cmd} --help"
	return get_cmd_output(cmd, cwd=sites_path, _raise=False)


def _parse_click_help(help_text: str) -> dict:
	commands = []
	options = []
	value_options = []
	section = None

	for raw_line in help_text.splitlines():
		line = raw_line.rstrip()
		stripped = line.strip()

		if stripped == "Options:":
			section = "options"
			continue
		if stripped == "Commands:":
			section = "commands"
			continue
		if not stripped:
			continue
		if not line.startswith("  "):
			section = None
			continue

		if section == "commands":
			commands.append(stripped.split()[0])
			continue

		if section == "options" and stripped.startswith("-"):
			for option_text in stripped.split("  ", 1)[0].split(","):
				option_text = option_text.strip()
				if not option_text.startswith("-"):
					continue
				parts = option_text.split()
				options.append(parts[0])
				if len(parts) > 1:
					value_options.append(parts[0])

	return {
		"commands": _unique(commands),
		"options": _unique(options),
		"value_options": _unique(value_options),
	}


def _detect_shell() -> str | None:
	shell = os.environ.get("SHELL", "").rsplit("/", 1)[-1]
	return shell if shell in {"bash", "zsh"} else None


def _default_completion_path(shell: str) -> Path:
	return Path.home() / ".config" / "bench" / f"completion.{shell}"


def _default_rc_file(shell: str) -> Path:
	return Path.home() / f".{shell}rc"


def _loader_line(path: Path) -> str:
	return f"source {shlex.quote(str(path))}"


def _ensure_line(path: Path, line: str) -> bool:
	path.parent.mkdir(parents=True, exist_ok=True)
	if path.exists():
		content = path.read_text(encoding="utf-8")
		if line in content:
			return False
	else:
		content = ""

	with path.open("a", encoding="utf-8") as handle:
		if content and not content.endswith("\n"):
			handle.write("\n")
		handle.write(line)
		handle.write("\n")

	return True


def _collect_command_tree(
	command: click.Command, path, subcommands, options, value_options
):
	key = _path_key(path)
	command_options = ["--help"]
	command_value_options = []

	for param in command.params:
		if not isinstance(param, click.Option):
			continue

		flags = _unique([*param.opts, *param.secondary_opts])
		command_options.extend(flags)

		if _option_takes_value(param):
			command_value_options.extend(flags)

	options[key] = _unique(command_options)
	value_options[key] = _unique(command_value_options)

	command_map = getattr(command, "commands", None)
	if command_map is not None:
		children = _unique(list(command_map.keys()))
		subcommands[key] = children

		for name, child in command_map.items():
			_collect_command_tree(
				child, (*path, name), subcommands, options, value_options
			)
	else:
		subcommands[key] = []


def _option_takes_value(option: click.Option) -> bool:
	return not option.is_flag and option.nargs != 0


def _path_key(path) -> str:
	return " ".join(path) if path else ROOT_KEY


def _unique(values):
	return list(dict.fromkeys(value for value in values if value))


def render_bash_completion(spec: dict) -> str:
	return _render_completion_script(spec, shell="bash")


def render_zsh_completion(spec: dict) -> str:
	return _render_completion_script(spec, shell="zsh")


def _render_completion_script(spec: dict, shell: str) -> str:
	parts = []

	if shell == "zsh":
		parts.extend(
			[
				"#compdef bench",
				"autoload -U bashcompinit",
				"bashcompinit",
				"",
			]
		)

	parts.extend(
		[
			"# shellcheck shell=bash",
			f"_BENCH_ROOT_KEY={shlex.quote(ROOT_KEY)}",
			f"_BENCH_FRAPPE_KEY={shlex.quote(FRAPPE_KEY)}",
			f"_BENCH_FRAPPE_COMMANDS={shlex.quote(' '.join(spec['frappe_commands']))}",
			f"_BENCH_FORWARDED_FLAGS={shlex.quote(' '.join(FORWARDED_FLAGS))}",
			f"_BENCH_FORWARDED_VALUE_OPTIONS={shlex.quote(' '.join(FORWARDED_VALUE_OPTIONS))}",
			"",
			_render_case_function("_bench_subcommands_for", spec["subcommands"]),
			"",
			_render_case_function("_bench_options_for", spec["options"]),
			"",
			_render_case_function("_bench_value_options_for", spec["value_options"]),
			"",
			_BASH_RUNTIME,
			"",
			"complete -o nosort -F _bench_completion bench",
		]
	)

	return "\n".join(parts) + "\n"


def _render_case_function(name: str, mapping: dict) -> str:
	lines = [f"{name}() {{", '\tcase "$1" in']

	for key, values in mapping.items():
		joined = " ".join(values)
		lines.append(f"\t\t{shlex.quote(key)}) printf '%s' {shlex.quote(joined)} ;;")

	lines.extend(["\t\t*) printf '%s' '' ;;", "\tesac", "}"])
	return "\n".join(lines)


_BASH_RUNTIME = r"""_bench_find_root() {
	local dir="$PWD"

	while [[ -n "$dir" && "$dir" != "/" ]]; do
		if [[ -d "$dir/apps" && -d "$dir/sites" && -d "$dir/config" && -d "$dir/logs" ]]; then
			printf '%s\n' "$dir"
			return 0
		fi
		dir="${dir%/*}"
		if [[ -z "$dir" ]]; then
			break
		fi
	done

	return 1
}

_bench_list_sites() {
	local root
	local path
	local site

	root="$(_bench_find_root)" || return 0

	for path in "$root"/sites/*/site_config.json; do
		[[ -f "$path" ]] || continue
		site="${path%/site_config.json}"
		site="${site##*/}"
		printf '%s\n' "$site"
	done
}

_bench_list_apps() {
	local root
	local path
	local app

	root="$(_bench_find_root)" || return 0

	if [[ -f "$root/sites/apps.txt" ]]; then
		while IFS= read -r path; do
			[[ -n "$path" ]] || continue
			printf '%s\n' "$path"
		done < "$root/sites/apps.txt"
		return 0
	fi

	for path in "$root"/apps/*; do
		[[ -d "$path" ]] || continue
		app="${path##*/}"
		printf '%s\n' "$app"
	done
}

_bench_has_word() {
	local needle="$1"
	local haystack="$2"
	local word

	for word in $haystack; do
		[[ "$word" == "$needle" ]] && return 0
	done

	return 1
}

_bench_join_path() {
	if [[ "$1" == "$_BENCH_ROOT_KEY" ]]; then
		printf '%s' "$2"
		return 0
	fi

	printf '%s %s' "$1" "$2"
}

_bench_collect_context() {
	local path="$_BENCH_ROOT_KEY"
	local skip_next=0
	local index
	local token
	local value_opts
	local subcommands

	for ((index = 1; index < COMP_CWORD; index++)); do
		token="${COMP_WORDS[index]}"

		if (( skip_next )); then
			skip_next=0
			continue
		fi

		if [[ "$token" == "--" ]]; then
			break
		fi

		value_opts="$(_bench_value_options_for "$path")"
		if [[ "$path" == "$_BENCH_ROOT_KEY" ]]; then
			value_opts="$value_opts $_BENCH_FORWARDED_VALUE_OPTIONS"
		fi

		if _bench_has_word "$token" "$value_opts"; then
			skip_next=1
			continue
		fi

		if [[ "$token" == -* ]]; then
			continue
		fi

		subcommands="$(_bench_subcommands_for "$path")"
		if _bench_has_word "$token" "$subcommands"; then
			path="$(_bench_join_path "$path" "$token")"
			continue
		fi

		if [[ "$path" == "$_BENCH_ROOT_KEY" ]] && _bench_has_word "$token" "$_BENCH_FRAPPE_COMMANDS"; then
			path="$_BENCH_FRAPPE_KEY"
		fi
	done

	printf '%s' "$path"
}

_bench_complete_words() {
	local cur="$1"
	local words="$2"

	COMPREPLY=( $(compgen -W "$words" -- "$cur") )
}

_bench_lines_to_words() {
	local lines="$1"

	printf '%s' "${lines//$'\n'/ }"
}

_bench_completion() {
	local cur="${COMP_WORDS[COMP_CWORD]}"
	local prev=""
	local path
	local words
	local options
	local subcommands
	local dynamic_words

	COMPREPLY=()

	if (( COMP_CWORD > 0 )); then
		prev="${COMP_WORDS[COMP_CWORD-1]}"
	fi

	case "$prev" in
		--site|-s)
			dynamic_words="$(_bench_list_sites)"
			dynamic_words="$(_bench_lines_to_words "$dynamic_words")"
			_bench_complete_words "$cur" "$dynamic_words"
			return 0
			;;
		--app)
			dynamic_words="$(_bench_list_apps)"
			dynamic_words="$(_bench_lines_to_words "$dynamic_words")"
			_bench_complete_words "$cur" "$dynamic_words"
			return 0
			;;
	esac

	path="$(_bench_collect_context)"
	options="$(_bench_options_for "$path")"
	subcommands="$(_bench_subcommands_for "$path")"

	if [[ "$path" == "$_BENCH_ROOT_KEY" ]]; then
		subcommands="$subcommands $_BENCH_FRAPPE_COMMANDS"
		options="$options $_BENCH_FORWARDED_FLAGS $_BENCH_FORWARDED_VALUE_OPTIONS"
	elif [[ "$path" == "$_BENCH_FRAPPE_KEY" ]]; then
		options="$_BENCH_FORWARDED_FLAGS $_BENCH_FORWARDED_VALUE_OPTIONS"
	fi

	if [[ "$cur" == -* ]]; then
		words="$options"
	else
		words="$subcommands $options"
	fi

	_bench_complete_words "$cur" "$words"
	return 0
}"""
