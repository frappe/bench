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

# Substrings matched against normalized option/argument names when Click does not
# declare an explicit click.Path type (common in older frappe command definitions).
_PATH_NAME_HINTS = ("path", "file", "certificate", "sql", "clone_from")

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
	path_options = {}
	path_positionals = {}

	_collect_command_tree(
		root_command, (), subcommands, options, value_options, path_options, path_positionals
	)

	bench_path = _find_current_bench_path()
	frappe_commands = []
	if bench_path:
		frappe_commands = _unique(get_env_frappe_commands(bench_path))
		_collect_frappe_tree(
			bench_path,
			subcommands,
			options,
			value_options,
			path_options,
			path_positionals,
			frappe_commands,
			verbose=verbose,
		)

	return {
		"subcommands": subcommands,
		"options": options,
		"value_options": value_options,
		"path_options": path_options,
		"path_positionals": path_positionals,
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
	bench_path,
	subcommands,
	options,
	value_options,
	path_options,
	path_positionals,
	fallback_commands,
	verbose: bool = True,
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
			path_options[key] = entry.get("path_options", [])
			path_positionals[key] = entry.get("path_positionals", [])
		return

	# get_app_groups() isn't available on older frappe versions, so fall back to
	# spawning one --help subprocess per command, parallelised across each BFS level.
	_collect_frappe_tree_bfs(
		bench_path,
		subcommands,
		options,
		value_options,
		path_options,
		path_positionals,
		fallback_commands,
	)


def _collect_frappe_tree_bfs(
	bench_path,
	subcommands,
	options,
	value_options,
	path_options,
	path_positionals,
	fallback_commands,
):
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
				path_options[key] = _unique(
					[
						option
						for option in parsed["value_options"]
						if _looks_like_path_option(option)
					]
				)
				path_positionals[key] = _unique(parsed["path_positionals"])
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

	path_positionals = []
	for raw_line in help_text.splitlines():
		stripped = raw_line.strip()
		if not stripped.startswith("Usage:"):
			continue
		path_positionals.extend(
			str(index)
			for index, token in enumerate(_usage_positional_tokens(stripped))
			if _looks_like_path_name(token)
		)
		break

	return {
		"commands": _unique(commands),
		"options": _unique(options),
		"value_options": _unique(value_options),
		"path_positionals": _unique(path_positionals),
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
	command: click.Command,
	path,
	subcommands,
	options,
	value_options,
	path_options,
	path_positionals,
):
	key = _path_key(path)
	command_options = ["--help"]
	command_value_options = []
	command_path_options = []
	command_path_positionals = []
	positional_index = 0

	for param in command.params:
		if isinstance(param, click.Option):
			flags = _unique([*param.opts, *param.secondary_opts])
			command_options.extend(flags)

			if _option_takes_value(param):
				command_value_options.extend(flags)
				if _param_expects_path(param):
					command_path_options.extend(flags)
			continue

		if isinstance(param, click.Argument):
			if _param_expects_path(param):
				command_path_positionals.append(str(positional_index))
			positional_index += 1

	options[key] = _unique(command_options)
	value_options[key] = _unique(command_value_options)
	path_options[key] = _unique(command_path_options)
	path_positionals[key] = _unique(command_path_positionals)

	command_map = getattr(command, "commands", None)
	if command_map is not None:
		children = _unique(list(command_map.keys()))
		subcommands[key] = children

		for name, child in command_map.items():
			_collect_command_tree(
				child,
				(*path, name),
				subcommands,
				options,
				value_options,
				path_options,
				path_positionals,
			)
	else:
		subcommands[key] = []


def _option_takes_value(option: click.Option) -> bool:
	return not option.is_flag and option.nargs != 0


def _normalize_param_name(name: str) -> str:
	return name.lower().replace("-", "_")


def _looks_like_path_name(name: str) -> bool:
	normalized = _normalize_param_name(name)
	return any(hint in normalized for hint in _PATH_NAME_HINTS)


def _looks_like_path_option(option: str) -> bool:
	return _looks_like_path_name(option.lstrip("-"))


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


def _usage_positional_tokens(usage_line: str) -> list[str]:
	import re

	usage = usage_line.split(":", 1)[-1].strip()
	usage = re.sub(r"\[[^\]]*\]", "", usage)
	tokens = re.findall(r"\b[A-Z][A-Z0-9_-]*\b", usage)
	return [token for token in tokens if token not in {"OPTIONS", "ARGS", "COMMAND"}]


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
			_render_case_function("_bench_path_options_for", spec["path_options"]),
			"",
			_render_case_function("_bench_path_positionals_for", spec["path_positionals"]),
			"",
			_render_bash_runtime(shell),
			"",
			"complete -o nosort -o nospace -F _bench_completion bench",
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


def _render_bash_runtime(shell: str) -> str:
	complete_files = (
		_BENCH_COMPLETE_FILES_ZSH if shell == "zsh" else _BENCH_COMPLETE_FILES_BASH
	)
	suffix = _BASH_RUNTIME_SUFFIX
	if shell == "zsh":
		suffix = suffix.replace(
			"_bench_completion() {\n\tlocal cur=",
			"_bench_completion() {\n\temulate -L sh\n\tlocal cur=",
			1,
		)
	return _BASH_RUNTIME_PREFIX + complete_files + suffix


_BASH_RUNTIME_PREFIX = r"""_bench_find_root() {
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
	local ctx="$_BENCH_ROOT_KEY"
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

		value_opts="$(_bench_value_options_for "$ctx")"
		if [[ "$ctx" == "$_BENCH_ROOT_KEY" ]]; then
			value_opts="$value_opts $_BENCH_FORWARDED_VALUE_OPTIONS"
		fi

		if _bench_has_word "$token" "$value_opts"; then
			skip_next=1
			continue
		fi

		if [[ "$token" == -* ]]; then
			continue
		fi

		subcommands="$(_bench_subcommands_for "$ctx")"
		if _bench_has_word "$token" "$subcommands"; then
			ctx="$(_bench_join_path "$ctx" "$token")"
			continue
		fi

		if [[ "$ctx" == "$_BENCH_ROOT_KEY" ]] && _bench_has_word "$token" "$_BENCH_FRAPPE_COMMANDS"; then
			ctx="$(_bench_join_path "$_BENCH_FRAPPE_KEY" "$token")"
			continue
		fi
	done

	printf '%s' "$ctx"
}

_bench_collect_completion_state() {
	local ctx="$_BENCH_ROOT_KEY"
	local positional_index=0
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

		value_opts="$(_bench_value_options_for "$ctx")"
		if [[ "$ctx" == "$_BENCH_ROOT_KEY" ]]; then
			value_opts="$value_opts $_BENCH_FORWARDED_VALUE_OPTIONS"
		fi

		if _bench_has_word "$token" "$value_opts"; then
			skip_next=1
			continue
		fi

		if [[ "$token" == -* ]]; then
			continue
		fi

		subcommands="$(_bench_subcommands_for "$ctx")"
		if _bench_has_word "$token" "$subcommands"; then
			ctx="$(_bench_join_path "$ctx" "$token")"
			positional_index=0
			continue
		fi

		if [[ "$ctx" == "$_BENCH_ROOT_KEY" ]] && _bench_has_word "$token" "$_BENCH_FRAPPE_COMMANDS"; then
			ctx="$(_bench_join_path "$_BENCH_FRAPPE_KEY" "$token")"
			positional_index=0
			continue
		fi

		((positional_index++))
	done

	printf '%s|%s' "$ctx" "$positional_index"
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

"""

_BENCH_COMPLETE_FILES_BASH = r"""_bench_expand_tilde() {
	local cur="$1"

	if [[ "$cur" == "~" || "$cur" == "~/"* ]]; then
		printf '%s' "${cur/#\~/$HOME}"
		return 0
	fi

	printf '%s' "$cur"
}

_bench_complete_files() {
	local cur="$1"
	local expanded
	local use_tilde=0
	local i

	if [[ "$cur" == "~" || "$cur" == "~/"* ]]; then
		use_tilde=1
	fi

	expanded="$(_bench_expand_tilde "$cur")"

	compopt -o filenames 2>/dev/null
	COMPREPLY=( $(compgen -f -- "$expanded") )

	for ((i = 0; i < ${#COMPREPLY[@]}; i++)); do
		if [[ -d "${COMPREPLY[i]}" && "${COMPREPLY[i]}" != */ ]]; then
			COMPREPLY[i]+=/
		fi

		if (( use_tilde )) && [[ "${COMPREPLY[i]}" == "$HOME"/* || "${COMPREPLY[i]}" == "$HOME" ]]; then
			COMPREPLY[i]="~${COMPREPLY[i]#$HOME}"
		fi
	done
}

"""

_BENCH_COMPLETE_FILES_ZSH = r"""_bench_expand_tilde() {
	local cur="$1"

	if [[ "$cur" == "~" || "$cur" == "~/"* ]]; then
		printf '%s' "${cur/#\~/$HOME}"
		return 0
	fi

	printf '%s' "$cur"
}

_bench_path_match_candidates() {
	local expanded="$1"
	local dir prefix

	if [[ -d "$expanded" ]]; then
		find "$expanded" -mindepth 1 -maxdepth 1 -print 2>/dev/null
		return 0
	fi

	if [[ "$expanded" == */* ]]; then
		dir="${expanded%/*}"
		prefix="${expanded##*/}"
	else
		dir="."
		prefix="$expanded"
	fi

	find "$dir" -maxdepth 1 -name "${prefix}"'*' -print 2>/dev/null
}

_bench_complete_files() {
	local cur="$1"
	local expanded use_tilde=0
	local match
	local i

	if [[ "$cur" == "~" || "$cur" == "~/"* ]]; then
		use_tilde=1
	fi

	expanded="$(_bench_expand_tilde "$cur")"
	COMPREPLY=()

	while IFS= read -r match; do
		[[ -n "$match" ]] || continue

		if [[ -d "$match" && "$match" != */ ]]; then
			match="${match}/"
		fi

		if (( use_tilde )) && [[ "$match" == "$HOME"/* || "$match" == "$HOME" ]]; then
			match="~${match#$HOME}"
		fi

		COMPREPLY+=("$match")
	done < <(_bench_path_match_candidates "$expanded")
}

"""

_BASH_RUNTIME_SUFFIX = r"""_bench_completion() {
	local cur="${COMP_WORDS[COMP_CWORD]}"
	local prev=""
	local ctx
	local positional_index=0
	local words
	local options
	local subcommands
	local dynamic_words
	local path_options
	local path_positionals
	local state

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

	state="$(_bench_collect_completion_state)"
	ctx="${state%|*}"
	positional_index="${state##*|}"

	path_options="$(_bench_path_options_for "$ctx")"
	if _bench_has_word "$prev" "$path_options"; then
		_bench_complete_files "$cur"
		return 0
	fi

	path_positionals="$(_bench_path_positionals_for "$ctx")"
	if [[ "$cur" != -* ]] && _bench_has_word "$positional_index" "$path_positionals"; then
		_bench_complete_files "$cur"
		return 0
	fi

	options="$(_bench_options_for "$ctx")"
	subcommands="$(_bench_subcommands_for "$ctx")"

	if [[ "$ctx" == "$_BENCH_ROOT_KEY" ]]; then
		subcommands="$subcommands $_BENCH_FRAPPE_COMMANDS"
		options="$options $_BENCH_FORWARDED_FLAGS $_BENCH_FORWARDED_VALUE_OPTIONS"
	elif [[ "$ctx" == "$_BENCH_FRAPPE_KEY" || "$ctx" == "$_BENCH_FRAPPE_KEY "* ]]; then
		options="$options $_BENCH_FORWARDED_FLAGS $_BENCH_FORWARDED_VALUE_OPTIONS"
	fi

	if [[ "$cur" == -* ]]; then
		words="$options"
	else
		words="$subcommands $options"
	fi

	_bench_complete_words "$cur" "$words"
	return 0
}"""
