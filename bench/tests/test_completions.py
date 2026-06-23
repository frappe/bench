import os
import shlex
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from bench.commands import bench_command
from bench.commands.completions import (
	_loader_line,
	_looks_like_path_name,
	_looks_like_path_option,
	_parse_click_help,
	generate_completion,
)


def _run_zsh_completion(script_path: str, words: list[str], cwd: str | None = None, env=None):
	quoted_words = " ".join(shlex.quote(word) for word in words)
	command = (
		f"autoload -Uz compinit; compinit -C; "
		f"source {shlex.quote(script_path)}; "
		"_files() { compadd \"$HOME/downloads/backup.sql.gz\"; }; "
		"compadd() { reply=(\"$@\"); }; "
		f"words=({quoted_words}); CURRENT={len(words)}; curcontext=:bench:; "
		"_bench; printf '%s\\n' \"${reply[@]}\""
	)
	return subprocess.run(
		["zsh", "-c", command],
		check=True,
		capture_output=True,
		text=True,
		cwd=cwd,
		env=env,
	)


def _frappe_root_help(commands: list[str]) -> str:
	return (
		"Usage: frappe [OPTIONS] COMMAND [ARGS]...\n\n"
		"Options:\n"
		"  --site TEXT\n"
		"  --help      Show this message and exit.\n\n"
		"Commands:\n"
		+ "".join(f"  {command}\n" for command in commands)
	)


def _frappe_command_help(command: str, usage: str = "[OPTIONS]", options=()) -> str:
	return (
		f"Usage: frappe {command} {usage}\n\n"
		"Options:\n"
		+ "".join(f"  {option}\n" for option in options)
		+ "  --help              Show this message and exit.\n"
	)


def _fake_frappe_help(commands: list[str], help_by_command: dict[str, str] | None = None):
	help_by_command = help_by_command or {}

	def fake_help(cmd, cwd=".", _raise=True):
		for command, help_text in help_by_command.items():
			if f"frappe {command} --help" in cmd:
				return help_text
		return _frappe_root_help(commands)

	return fake_help


@contextmanager
def _mock_frappe_completion(commands: list[str], help_by_command: dict[str, str] | None = None):
	with tempfile.TemporaryDirectory() as bench_dir:
		bench_path = Path(bench_dir)
		(bench_path / "sites").mkdir()

		with (
			patch(
				"bench.commands.completions.get_env_frappe_commands",
				return_value=commands,
			),
			patch(
				"bench.commands.completions.find_parent_bench",
				return_value=bench_dir,
			),
			patch("bench.commands.completions.get_env_cmd", return_value="python"),
			patch("bench.commands.completions._get_frappe_spec_batch", return_value=None),
			patch(
				"bench.commands.completions.get_cmd_output",
				side_effect=_fake_frappe_help(commands, help_by_command),
			),
		):
			yield bench_path


def _generate_frappe_completion(
	shell: str,
	commands: list[str],
	help_by_command: dict[str, str] | None = None,
) -> str:
	with _mock_frappe_completion(commands, help_by_command):
		return generate_completion(shell, bench_command)


@contextmanager
def _temporary_completion_script(script: str, suffix: str):
	with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as handle:
		handle.write(script)
		script_path = handle.name

	try:
		yield script_path
	finally:
		Path(script_path).unlink(missing_ok=True)


def _run_bash_completion_script(
	script: str,
	command: str,
	cwd: str | Path | None = None,
	env=None,
):
	with _temporary_completion_script(script, ".sh") as script_path:
		return subprocess.run(
			[
				"bash",
				"-c",
				f"source {shlex.quote(script_path)} >/dev/null 2>&1 || true; {command}",
			],
			check=True,
			capture_output=True,
			text=True,
			cwd=cwd,
			env=env,
		)


class TestBenchCompletionGeneration(unittest.TestCase):
	def assertContainsAll(self, script: str, snippets):
		for snippet in snippets:
			with self.subTest(snippet=snippet):
				self.assertIn(snippet, script)

	def assertContainsNone(self, script: str, snippets):
		for snippet in snippets:
			with self.subTest(snippet=snippet):
				self.assertNotIn(snippet, script)

	def test_bash_completion_is_shell_only(self):
		script = generate_completion("bash", bench_command)

		self.assertContainsAll(
			script,
			[
				"_bench_subcommands_for()",
				"complete -o nosort -o nospace -F _bench_completion bench",
			],
		)
		self.assertContainsNone(script, ["_BENCH_COMPLETE"])

	def test_generation_embeds_current_frappe_commands(self):
		script = _generate_frappe_completion(
			"bash",
			["migrate", "list-apps", "migrate"],
			{
				"migrate": _frappe_command_help(
					"migrate",
					options=["--skip-failing TEXT"],
				),
				"list-apps": _frappe_command_help(
					"list-apps",
					options=["--format TEXT"],
				),
			},
		)

		self.assertIn("_BENCH_FRAPPE_COMMANDS='migrate list-apps'", script)
		self.assertIn("__frappe__) printf '%s' 'migrate list-apps'", script)
		self.assertIn("__frappe__) printf '%s' '--help --site'", script)
		self.assertIn(
			"'__frappe__ migrate') printf '%s' '--help --skip-failing'", script
		)

	def test_zsh_completion_uses_native_compdef(self):
		script = generate_completion("zsh", bench_command)

		self.assertContainsAll(
			script,
			["#compdef bench", "compdef _bench bench", "_bench() {", "_files"],
		)
		self.assertContainsNone(
			script,
			[
				"bashcompinit",
				"emulate -L sh",
				"_bench_completion()",
				"complete -o nosort",
				"_bench_path_match_candidates()",
			],
		)

	def test_runtime_avoids_external_coreutils(self):
		script = generate_completion("bash", bench_command)

		self.assertContainsNone(script, ["tr '\\n' ' '", "dirname", "basename"])

	def test_bash_completion_includes_file_path_helpers(self):
		script = generate_completion("bash", bench_command)

		self.assertContainsAll(
			script,
			[
				"_bench_path_options_for()",
				"_bench_path_positionals_for()",
				"_bench_complete_files()",
				"compgen -f",
				"complete -o nosort -o nospace -F _bench_completion bench",
				"_bench_expand_tilde()",
				'COMPREPLY[i]="~${COMPREPLY[i]#$HOME}"',
			],
		)
		self.assertContainsNone(
			script,
			['matches=("$dir"/${base}*(N))', "_bench_path_match_candidates()"],
		)

	def test_bench_init_registers_path_completion(self):
		script = generate_completion("bash", bench_command)

		self.assertContainsAll(
			script,
			["init) printf '%s' 0", "--frappe-path", "--clone-from"],
		)

	def test_help_fallback_detects_path_options_and_positionals(self):
		parsed = _parse_click_help(
			"Usage: bench restore [OPTIONS] SQL-FILE-PATH\n\n"
			"Options:\n"
			"  --with-public-files PATH\n"
			"  --with-private-files PATH\n"
			"  --help              Show this message and exit.\n"
		)

		self.assertEqual(parsed["path_positionals"], ["0"])
		self.assertEqual(
			parsed["value_options"],
			["--with-public-files", "--with-private-files"],
		)
		self.assertTrue(_looks_like_path_option("--with-public-files"))
		self.assertTrue(_looks_like_path_option("--backup-path"))
		self.assertFalse(_looks_like_path_option("--format"))

	def test_path_name_heuristics(self):
		self.assertTrue(_looks_like_path_name("sql-file-path"))
		self.assertTrue(_looks_like_path_name("ssl-certificate-key"))
		self.assertTrue(_looks_like_path_name("clone-from"))
		self.assertFalse(_looks_like_path_name("format"))

	def test_frappe_restore_path_completion_via_help_fallback(self):
		script = _generate_frappe_completion(
			"bash",
			["restore", "backup"],
			{
				"restore": _frappe_command_help(
					"restore",
					"[OPTIONS] SQL-FILE-PATH",
					["--with-public-files PATH", "--with-private-files PATH"],
				),
				"backup": _frappe_command_help(
					"backup",
					options=["--backup-path PATH"],
				),
			},
		)

		self.assertIn("'__frappe__ restore') printf '%s' 0", script)
		self.assertIn("--with-public-files", script)
		self.assertIn("--with-private-files", script)
		self.assertIn("--backup-path", script)

	def test_runtime_resolves_frappe_subcommand_context(self):
		with _mock_frappe_completion(["restore"]):
			script = generate_completion("bash", bench_command)

			self.assertIn(
				'ctx="$(_bench_join_path "$_BENCH_FRAPPE_KEY" "$token")"',
				script,
			)

			result = _run_bash_completion_script(
				script,
				"COMP_WORDS=(bench restore ''); COMP_CWORD=2; "
				"_bench_collect_completion_state",
			)

		self.assertEqual(result.stdout.strip(), "__frappe__ restore|0")

	def test_runtime_completes_files_for_restore(self):
		with _mock_frappe_completion(
			["restore"],
			{
				"restore": _frappe_command_help(
					"restore",
					"[OPTIONS] SQL-FILE-PATH",
					["--with-public-files PATH"],
				),
			},
		) as bench_dir:
			script = generate_completion("bash", bench_command)

			result = _run_bash_completion_script(
				script,
				"touch marker-restore-test; "
				"COMP_WORDS=(bench restore ''); COMP_CWORD=2; "
				"_bench_completion; "
				'printf "%s\\n" "${COMPREPLY[@]}"',
				cwd=bench_dir,
			)

		self.assertIn("marker-restore-test", result.stdout.splitlines())

	def test_runtime_appends_slash_to_completed_directories(self):
		with _mock_frappe_completion(
			["restore"],
			{"restore": _frappe_command_help("restore", "[OPTIONS] SQL-FILE-PATH")},
		) as bench_dir:
			(bench_dir / "nested-dir").mkdir()
			script = generate_completion("bash", bench_command)

			result = _run_bash_completion_script(
				script,
				"COMP_WORDS=(bench restore nested); COMP_CWORD=2; "
				"COMP_WORDS+=( '' ); COMP_CWORD=2; "
				"_bench_completion; "
				'printf "%s\\n" "${COMPREPLY[@]}"',
				cwd=bench_dir,
			)

		self.assertIn("nested-dir/", result.stdout.splitlines())

	def test_runtime_completes_tilde_paths_after_forwarded_site(self):
		with _mock_frappe_completion(
			["restore"],
			{"restore": _frappe_command_help("restore", "[OPTIONS] SQL-FILE-PATH")},
		) as bench_dir:
			downloads = bench_dir / "downloads"
			downloads.mkdir()
			(downloads / "backup.sql.gz").write_text("x", encoding="utf-8")
			script = generate_completion("bash", bench_command)

			result = _run_bash_completion_script(
				script,
				"COMP_WORDS=(bench restore --site mysite '~/downloads/b'); COMP_CWORD=4; "
				"_bench_completion; "
				'printf "%s\\n" "${COMPREPLY[@]}"',
				cwd=bench_dir,
				env={**os.environ, "HOME": str(bench_dir)},
			)

		self.assertIn("~/downloads/backup.sql.gz", result.stdout.splitlines())

	def test_zsh_runtime_resolves_frappe_subcommand_context(self):
		script = _generate_frappe_completion("zsh", ["restore"])

		with _temporary_completion_script(script, ".zsh") as script_path:
			result = subprocess.run(
				[
					"zsh",
					"-c",
					f"source {shlex.quote(script_path)}; "
					"words=(bench restore); CURRENT=3; "
					"_bench_collect_completion_state",
				],
				check=True,
				capture_output=True,
				text=True,
			)

		self.assertEqual(result.stdout.strip(), "__frappe__ restore|0")

	def test_zsh_completion_handles_partial_command_without_error(self):
		script = generate_completion("zsh", bench_command)

		with _temporary_completion_script(script, ".zsh") as script_path:
			result = _run_zsh_completion(script_path, ["bench", "rest"])

		self.assertNotIn("_bench_has_word", result.stderr)
		self.assertEqual(result.returncode, 0)

	def test_zsh_completion_uses_tilde_paths_after_forwarded_site(self):
		with _mock_frappe_completion(
			["restore"],
			{"restore": _frappe_command_help("restore", "[OPTIONS] SQL-FILE-PATH")},
		) as bench_dir:
			downloads = bench_dir / "downloads"
			downloads.mkdir()
			(downloads / "backup.sql.gz").write_text("x", encoding="utf-8")
			script = generate_completion("zsh", bench_command)

			with _temporary_completion_script(script, ".zsh") as script_path:
				result = _run_zsh_completion(
					script_path,
					["bench", "restore", "--site", "mysite", "~/downloads/b"],
					cwd=bench_dir,
					env={**os.environ, "HOME": str(bench_dir)},
				)

		self.assertTrue(
			any("backup.sql.gz" in line for line in result.stdout.splitlines()),
			result.stdout,
		)

	def test_non_interactive_writes_script_and_rc_loader(self):
		runner = CliRunner()
		with runner.isolated_filesystem():
			completion_path = Path("completion.zsh").resolve()
			rc_path = Path(".zshrc").resolve()

			result = runner.invoke(
				bench_command,
				[
					"completions",
					"--zsh",
					"--path",
					str(completion_path),
					"--rc-file",
					str(rc_path),
					"--yes",
				],
			)

			self.assertEqual(result.exit_code, 0)
			self.assertTrue(completion_path.exists())
			self.assertTrue(rc_path.exists())
			self.assertIn(_loader_line(completion_path), rc_path.read_text())
