# imports - standard imports
import os
import re
import shlex
import shutil
import subprocess
from typing import List, Optional, Tuple

# imports - third party imports
import click
import requests

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
MAX_HELP_CHARS = 12000
MAX_BENCH_PATH_LIST_CHARS = 12000
MAX_FRAPPE_HELP_CHARS = 20000
MAX_FRAPPE_NAMES_CHARS = 12000

# Fallback when we can't run bench_helper (e.g. not inside a bench). Tokens align with Frappe docs.
COMMON_FRAPPE_COMMANDS_CRIB = """Common Frappe framework command names (short crib; same commands are listed in Frappe docs).
They usually run as `bench <name>` (bench forwards to Frappe) or `bench --site <site> <name>` when a site is required:
doctor, migrate, console, backup, restore, install-app, uninstall-app, reinstall-app, list-apps, show-config,
clear-cache, clear-website-cache, build, version, scheduler, worker, mariadb, execute, data-import, export-csv,
serve, reload-doc, reload-doctype, disable-scheduler, enable-scheduler, set-admin-password, set-config, use,
browse, drop-site, partial-restore, transform-database, trim-database, trim-tables, rebuild-global-search

Your machine’s complete set appears in Context only when bench-ai runs inside a Frappe bench with a working env."""

COMMON_FRAPPE_FIRST_TOKENS = frozenset(
	{
		"doctor",
		"migrate",
		"console",
		"backup",
		"restore",
		"install-app",
		"uninstall-app",
		"reinstall-app",
		"list-apps",
		"show-config",
		"clear-cache",
		"clear-website-cache",
		"build",
		"version",
		"scheduler",
		"worker",
		"mariadb",
		"execute",
		"data-import",
		"export-csv",
		"serve",
		"reload-doc",
		"reload-doctype",
		"disable-scheduler",
		"enable-scheduler",
		"set-admin-password",
		"set-config",
		"use",
		"browse",
		"drop-site",
		"partial-restore",
		"transform-database",
		"trim-database",
		"trim-tables",
		"rebuild-global-search",
	}
)

CHEATSHEET = """Typical frappe-bench flows:
- New bench: clones Frappe into apps/, env, sites/, config — `bench init <path>`
- New site: `bench new-site <site>`
- Get app from Git (into apps/): `bench get-app <app> [git-url]` — not the same as installing on a site
- Install app on a site: `bench --site <site> install-app <app>`
- ERPNext example: `bench get-app erpnext`, then `bench --site <site> install-app erpnext`, often `migrate` / `bench build`
- Framework commands (`doctor`, `migrate`, `console`, …): `bench --site <site> <cmd>` or `bench <cmd>` when bench delegates to Frappe; full list only when bench-ai runs inside a working bench
- Dev: `bench start` · Update: `bench update` · Migrate site: `bench --site <site> migrate`
- Backup: `bench --site <site> backup [--with-files]` · All sites: `bench backup-all-sites`
"""

BENCH_AI_LONG_DOC = """Suggest bench commands from plain English via an OpenAI-compatible Chat Completions API.

Examples:
  bench-ai "back up all sites"
  bench-ai "install erpnext on site erp.local" --temperature 0
  bench-ai "what command migrates my database?" --dry-run

What it does: finds your bench root if possible, builds context from local `bench --help` (and Frappe appendix
when inside a bench), sends that plus your question to the API, prints the reply and a parsed `bench …` line.

Environment:
  BENCH_AI_API_KEY or OPENAI_API_KEY (required unless --dry-run)
  BENCH_AI_BASE_URL — default https://api.openai.com/v1
  BENCH_AI_MODEL — default gpt-4o-mini

By default nothing is executed. --run asks for confirmation, then runs the parsed argv without a shell."""


def _print_help(ctx: click.Context, param, value: bool):
	if not value or ctx.resilient_parsing:
		return
	click.echo(click.style("bench-ai", fg="cyan", bold=True) + " — natural language to bench command")
	click.echo()
	click.echo("Usage: bench-ai [OPTIONS] PROMPT")
	click.echo()
	click.echo(BENCH_AI_LONG_DOC.rstrip())
	click.echo()
	fmt = ctx.make_formatter()
	ctx.command.format_options(ctx, fmt)
	click.echo(fmt.getvalue().rstrip())
	ctx.exit()


def _rule_char_line():
	cols = shutil.get_terminal_size(fallback=(88, 24)).columns
	return "─" * min(max(cols - 4, 40), 72)


def normalize_base_url(url: str) -> str:
	url = (url or DEFAULT_BASE_URL).strip().rstrip("/")
	if not url.endswith("/v1"):
		url = url + "/v1"
	return url


def get_api_key() -> Optional[str]:
	return os.environ.get("BENCH_AI_API_KEY") or os.environ.get("OPENAI_API_KEY")


def collect_bench_click_paths(
	group: click.Group, prefix: Tuple[str, ...] = ()
) -> List[str]:
	paths: List[str] = []
	for name, cmd in group.commands.items():
		aliases: Tuple[str, ...] = (name,) if isinstance(name, str) else tuple(name)
		for part in aliases:
			path = prefix + (part,)
			paths.append(" ".join(path))
			if isinstance(cmd, click.Group):
				paths.extend(collect_bench_click_paths(cmd, path))
	return paths


def build_context() -> str:
	from bench.commands import bench_command

	sections: List[str] = [CHEATSHEET, COMMON_FRAPPE_COMMANDS_CRIB]

	native = sorted(set(collect_bench_click_paths(bench_command)))
	block = "Bench native subcommands (from Click; `bench <path>` without `--site`):\n" + "\n".join(native)
	if len(block) > MAX_BENCH_PATH_LIST_CHARS:
		block = block[: MAX_BENCH_PATH_LIST_CHARS - 3] + "...\n(list truncated)"
	sections.append(block)

	ctx = click.Context(bench_command)
	help_text = ctx.get_help()
	if len(help_text) > MAX_HELP_CHARS:
		help_text = help_text[: MAX_HELP_CHARS - 3] + "..."
	sections.append("Bench CLI help (top of `bench --help`):\n" + help_text)

	from bench.utils import get_env_frappe_commands, is_bench_directory

	if is_bench_directory():
		try:
			from bench.cli import get_frappe_help

			frappe_help = get_frappe_help()
			if frappe_help.strip():
				if len(frappe_help) > MAX_FRAPPE_HELP_CHARS:
					frappe_help = frappe_help[: MAX_FRAPPE_HELP_CHARS - 3] + "..."
				sections.append(
					"Framework commands (`bench --help` appendix on this bench):\n" + frappe_help.strip()
				)
		except Exception:
			pass
		try:
			cmds = get_env_frappe_commands()
			if cmds:
				names = sorted({str(c).strip() for c in cmds if str(c).strip()})
				line = (
					"Framework command names (`bench --site <site> <name>` …):\n" + ", ".join(names)
				)
				if len(line) > MAX_FRAPPE_NAMES_CHARS:
					line = line[: MAX_FRAPPE_NAMES_CHARS - 3] + "... (truncated)"
				sections.append(line)
		except Exception:
			pass
	else:
		sections.append(
			"Note: not inside a bench — live framework names/help omitted. `cd` to your bench for the full list."
		)

	return "\n\n".join(sections)


def chat_completion(
	base_url: str, api_key: str, model: str, temperature: float, messages: list
) -> str:
	endpoint = normalize_base_url(base_url) + "/chat/completions"
	resp = requests.post(
		endpoint,
		headers={
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json",
		},
		json={"model": model, "messages": messages, "temperature": temperature},
		timeout=120,
	)
	if resp.status_code == 401:
		raise click.ClickException(
			"API authentication failed (401). Check BENCH_AI_API_KEY or OPENAI_API_KEY."
		)
	if resp.status_code == 429:
		raise click.ClickException("Rate limited (429). Retry later.")
	try:
		resp.raise_for_status()
	except requests.HTTPError as e:
		raise click.ClickException(f"API request failed: {e}") from e
	data = resp.json()
	choices = data.get("choices") or []
	if not choices:
		raise click.ClickException("Empty response from API.")
	content = choices[0].get("message", {}).get("content")
	if not content:
		raise click.ClickException("No message content in API response.")
	return content.strip()


def _line_has_placeholders(line: str) -> bool:
	return "<" in line and ">" in line


def _skip_global_bench_flags(tokens: List[str], i: int) -> int:
	while i < len(tokens):
		t = tokens[i]
		if t in ("-v", "--verbose"):
			i += 1
			continue
		if t == "--version":
			i += 1
			continue
		if t == "--use-feature":
			if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
				i += 2
			else:
				i += 1
			continue
		break
	return i


def extract_bench_invocation(line: str) -> Optional[Tuple[str, List[str]]]:
	try:
		tokens = shlex.split(line)
	except ValueError:
		return None
	if not tokens or tokens[0] != "bench":
		return None
	i = _skip_global_bench_flags(tokens, 1)
	if i < len(tokens) and tokens[i] == "--site":
		if i + 1 >= len(tokens):
			return None
		i += 2
		i = _skip_global_bench_flags(tokens, i)
		return ("frappe", list(tokens[i:]))
	return ("bench", list(tokens[i:]))


def validate_bench_native_path(group: click.Group, parts: List[str]) -> Tuple[bool, str]:
	if not parts:
		return False, "Incomplete `bench` command (missing subcommand)."
	i = 0
	while i < len(parts):
		name = parts[i]
		if name not in group.commands:
			return False, f"Unknown bench CLI command `{name}` — not in your installed bench."
		cmd = group.commands[name]
		i += 1
		if isinstance(cmd, click.Group):
			if i >= len(parts):
				return True, ""
			group = cmd
			continue
		return True, ""
	return True, ""


def validate_frappe_subcommand(parts: List[str], frappe_names: set) -> Tuple[bool, str]:
	if not parts:
		return False, "Missing framework subcommand after `--site <site>`."
	head = parts[0]
	if head not in frappe_names:
		return False, f"Unknown framework command `{head}` — not in this bench's Frappe list."
	return True, ""


def load_frappe_command_names() -> Optional[set]:
	from bench.utils import get_env_frappe_commands, is_bench_directory

	if not is_bench_directory():
		return None
	try:
		raw = get_env_frappe_commands()
	except Exception:
		return None
	if not raw:
		return None
	names = {str(x).strip() for x in raw if str(x).strip()}
	return names or None


def validate_suggested_command_line(
	line: str,
	bench_root: click.Group,
	frappe_names: Optional[set],
) -> Tuple[bool, str]:
	if _line_has_placeholders(line):
		return True, ""
	parsed = extract_bench_invocation(line)
	if parsed is None:
		return False, "Could not parse a `bench ...` command from this line."
	kind, parts = parsed
	if kind == "frappe":
		if frappe_names is None:
			return True, ""
		return validate_frappe_subcommand(parts, frappe_names)
	ok, msg = validate_bench_native_path(bench_root, parts)
	if ok:
		return True, ""
	if frappe_names is not None:
		if parts and parts[0] in frappe_names:
			return validate_frappe_subcommand(parts, frappe_names)
		return ok, msg
	if parts and parts[0] in COMMON_FRAPPE_FIRST_TOKENS:
		return True, ""
	return ok, msg


_LINE_BENCH = re.compile(r"^\s*(?:[-*]\s+)?(?P<cmd>bench\s+.+)$")


def parse_suggested_command(text: str) -> str:
	found: List[str] = []
	for block in re.findall(
		r"```(?:bash|sh)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE
	):
		for raw in block.strip().splitlines():
			line = raw.strip()
			if line.startswith("bench "):
				found.append(line)
	for line in text.splitlines():
		m = _LINE_BENCH.match(line)
		if m:
			found.append(m.group("cmd").strip())
	for line in found:
		if not _line_has_placeholders(line):
			return line
	if found:
		return found[0]
	return ""


SYSTEM_PROMPT = """You help with frappe-bench CLI questions. Stick to the Context block: native subcommands from
this install, `bench --help`, optional live Frappe names/help inside a bench, plus a short static framework crib
when the live list is missing.

Rules:
- Native `bench` subcommands must appear in the "Bench native subcommands" list or Bench CLI help.
- Framework commands: first token must be in the live framework list or in "Common Frappe framework command names".
  If it isn't, do not put it in a ```bash fence.
- No invented flags or subcommands. If Context is insufficient, explain in prose and point to official Bench docs;
  leave ### Command to run without a bash fence.

Structure your answer as:

### Summary
### Command to run
### What this command does
### Recommended next steps

Keep ### What this command does factual for the commands you named. Be concise; don't paste Context back.
"""


@click.command(
	name="bench-ai",
	context_settings={"help_option_names": []},
	add_help_option=False,
)
@click.option(
	"-h",
	"--help",
	is_flag=True,
	is_eager=True,
	expose_value=False,
	callback=_print_help,
	help="Show usage and options.",
)
@click.argument("prompt", type=str, required=True, metavar="PROMPT")
@click.option("--model", "model", default=None, help="Overrides BENCH_AI_MODEL.")
@click.option(
	"--temperature",
	type=float,
	default=0.1,
	show_default=True,
	help="Sampling temperature.",
)
@click.option(
	"--dry-run",
	is_flag=True,
	help="Print model and context size only; no API call.",
)
@click.option(
	"--run",
	"run_cmd",
	is_flag=True,
	help="Confirm and run the suggested command (no shell).",
)
def bench_ai(prompt, model, temperature, dry_run, run_cmd):
	from bench.cli import change_working_directory
	from bench.commands import bench_command
	from bench.utils import is_bench_directory

	change_working_directory()

	if not is_bench_directory():
		click.secho(
			"Tip: not in a Frappe bench — using static framework crib; `cd` to your bench for full `bench --help`.",
			fg="yellow",
			dim=True,
		)
		click.echo()

	context = build_context()
	model_id = model or os.environ.get("BENCH_AI_MODEL") or DEFAULT_MODEL
	base_url = os.environ.get("BENCH_AI_BASE_URL", DEFAULT_BASE_URL)

	if dry_run:
		click.secho("bench-ai — dry run", fg="cyan", bold=True)
		click.echo()
		stats = [
			("Model", model_id),
			("API base", normalize_base_url(base_url)),
			("Context size", f"{len(context):,} chars"),
			("Prompt", f"{len(prompt):,} chars"),
		]
		w = max(len(k) for k, _ in stats)
		for k, v in stats:
			click.echo(f"  {k.ljust(w)}  {v}")
		click.echo()
		click.secho("No API request sent.", dim=True)
		return

	api_key = get_api_key()
	if not api_key:
		raise click.ClickException(
			"Missing API key. Set BENCH_AI_API_KEY or OPENAI_API_KEY, or use --dry-run."
		)

	messages = [
		{"role": "system", "content": SYSTEM_PROMPT},
		{
			"role": "user",
			"content": (
				"Context is authoritative; only use ```bash for commands that match it.\n\n"
				f"Context:\n{context}\n\nQuestion:\n{prompt}"
			),
		},
	]
	click.secho("Requesting suggestion…", fg="bright_black")
	reply = chat_completion(base_url, api_key, model_id, temperature, messages)

	click.echo()
	click.secho("Guidance", fg="bright_blue", bold=True)
	click.secho(
		"(From local bench help; suggested line is checked against this CLI.)",
		fg="bright_black",
		dim=True,
	)
	click.echo(click.style(_rule_char_line(), fg="bright_black"))
	click.echo(reply)

	frappe_names = load_frappe_command_names()
	suggested = parse_suggested_command(reply)
	is_bench_line = suggested.startswith("bench ")
	valid, err = (
		validate_suggested_command_line(suggested, bench_command, frappe_names)
		if is_bench_line
		else (True, "")
	)

	if is_bench_line:
		click.echo()
		click.secho("Suggested command (for --run)", fg="cyan", bold=True)
		click.echo(click.style(_rule_char_line(), fg="bright_black"))
		click.echo(click.style(suggested, fg="green", bold=True))
		click.echo()
		inv = extract_bench_invocation(suggested)
		if _line_has_placeholders(suggested):
			click.secho(
				"Line has <placeholders> — edit before running.",
				fg="yellow",
			)
		elif not valid:
			click.secho("Local validation failed", fg="red", bold=True)
			click.secho(err, fg="red")
			click.secho("Compare with `bench --help` before using this.", fg="yellow")
		elif inv and inv[0] == "frappe" and frappe_names is None:
			click.secho(
				"`--site` line not checked against live Frappe list (run bench-ai from a bench for that).",
				fg="yellow",
				dim=True,
			)
		elif valid and frappe_names is not None:
			click.secho("OK — matches this bench's CLI / Frappe commands.", fg="green", dim=True)
		elif valid:
			click.secho(
				"OK — native bench and/or crib (full framework list only on a real bench).",
				fg="green",
				dim=True,
			)
	else:
		click.echo()
		click.secho(
			"No `bench …` line in the reply (add a ```bash block). Running from a bench helps for framework commands.",
			fg="yellow",
		)

	if run_cmd:
		final = parse_suggested_command(reply)
		if not final.startswith("bench "):
			raise click.ClickException("Refusing --run: no runnable `bench ...` in the reply.")
		if _line_has_placeholders(final):
			raise click.ClickException("Refusing --run: fix <placeholders> first.")
		ok_run, run_err = validate_suggested_command_line(final, bench_command, frappe_names)
		if not ok_run:
			raise click.ClickException(
				f"Refusing --run: {run_err} Verify with `bench --help` and run manually if needed."
			)
		click.echo()
		if not click.confirm(click.style("Run this command?", fg="yellow") + f"\n  {final}", default=False):
			click.secho("Cancelled.", dim=True)
			return
		try:
			argv = shlex.split(final)
		except ValueError as e:
			raise click.ClickException(f"Could not parse command: {e}") from e
		click.secho("Running…", fg="bright_black")
		ret = subprocess.run(argv, check=False).returncode
		if ret:
			click.secho(f"Exit code: {ret}", fg="yellow")
		else:
			click.secho("Done.", fg="green")


def main():
	bench_ai()


if __name__ == "__main__":
	main()
