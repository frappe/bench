import os
import shlex
import subprocess
import tempfile
import unittest
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


class TestBenchCompletionGeneration(unittest.TestCase):
	def test_bash_completion_is_shell_only(self):
		script = generate_completion("bash", bench_command)

		self.assertIn("_bench_subcommands_for()", script)
		self.assertIn("complete -o nosort -o nospace -F _bench_completion bench", script)
		self.assertNotIn("_BENCH_COMPLETE", script)

	def test_generation_embeds_current_frappe_commands(self):
		def fake_help(cmd, cwd=".", _raise=True):
			if "frappe migrate --help" in cmd:
				return (
					"Usage: frappe migrate [OPTIONS]\n\n"
					"Options:\n"
					"  --skip-failing TEXT\n"
					"  --help              Show this message and exit.\n"
				)
			if "frappe list-apps --help" in cmd:
				return (
					"Usage: frappe list-apps [OPTIONS]\n\n"
					"Options:\n"
					"  --format TEXT\n"
					"  --help         Show this message and exit.\n"
				)
			return (
				"Usage: frappe [OPTIONS] COMMAND [ARGS]...\n\n"
				"Options:\n"
				"  --site TEXT\n"
				"  --help      Show this message and exit.\n\n"
				"Commands:\n"
				"  migrate\n"
				"  list-apps\n"
			)

		with (
			tempfile.TemporaryDirectory() as bench_dir,
			patch(
				"bench.commands.completions.get_env_frappe_commands",
				return_value=["migrate", "list-apps", "migrate"],
			),
			patch(
				"bench.commands.completions.find_parent_bench",
				return_value=bench_dir,
			),
			patch("bench.commands.completions.get_env_cmd", return_value="python"),
			patch("bench.commands.completions.get_cmd_output", side_effect=fake_help),
		):
			script = generate_completion("bash", bench_command)

		self.assertIn("_BENCH_FRAPPE_COMMANDS='migrate list-apps'", script)
		self.assertIn("__frappe__) printf '%s' 'migrate list-apps'", script)
		self.assertIn("__frappe__) printf '%s' '--help --site'", script)
		self.assertIn(
			"'__frappe__ migrate') printf '%s' '--help --skip-failing'", script
		)

	def test_zsh_completion_uses_native_compdef(self):
		script = generate_completion("zsh", bench_command)

		self.assertIn("#compdef bench", script)
		self.assertIn("compdef _bench bench", script)
		self.assertIn("_bench() {", script)
		self.assertIn("_files", script)
		self.assertNotIn("bashcompinit", script)
		self.assertNotIn("emulate -L sh", script)
		self.assertNotIn("_bench_completion()", script)
		self.assertNotIn("complete -o nosort", script)
		self.assertNotIn("_bench_path_match_candidates()", script)

	def test_runtime_avoids_external_coreutils(self):
		script = generate_completion("bash", bench_command)

		self.assertNotIn("tr '\\n' ' '", script)
		self.assertNotIn("dirname", script)
		self.assertNotIn("basename", script)

	def test_bash_completion_includes_file_path_helpers(self):
		script = generate_completion("bash", bench_command)

		self.assertIn("_bench_path_options_for()", script)
		self.assertIn("_bench_path_positionals_for()", script)
		self.assertIn("_bench_complete_files()", script)
		self.assertIn("compgen -f", script)
		self.assertNotIn('matches=("$dir"/${base}*(N))', script)
		self.assertNotIn("_bench_path_match_candidates()", script)
		self.assertIn("complete -o nosort -o nospace -F _bench_completion bench", script)
		self.assertIn("_bench_expand_tilde()", script)
		self.assertIn('COMPREPLY[i]="~${COMPREPLY[i]#$HOME}"', script)

	def test_bench_init_registers_path_completion(self):
		script = generate_completion("bash", bench_command)

		self.assertIn("init) printf '%s' 0", script)
		self.assertIn("--frappe-path", script)
		self.assertIn("--clone-from", script)

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
		def fake_help(cmd, cwd=".", _raise=True):
			if "frappe restore --help" in cmd:
				return (
					"Usage: frappe restore [OPTIONS] SQL-FILE-PATH\n\n"
					"Options:\n"
					"  --with-public-files PATH\n"
					"  --with-private-files PATH\n"
					"  --help              Show this message and exit.\n"
				)
			if "frappe backup --help" in cmd:
				return (
					"Usage: frappe backup [OPTIONS]\n\n"
					"Options:\n"
					"  --backup-path PATH\n"
					"  --help           Show this message and exit.\n"
				)
			return (
				"Usage: frappe [OPTIONS] COMMAND [ARGS]...\n\n"
				"Options:\n"
				"  --site TEXT\n"
				"  --help      Show this message and exit.\n\n"
				"Commands:\n"
				"  restore\n"
				"  backup\n"
			)

		with (
			tempfile.TemporaryDirectory() as bench_dir,
			patch(
				"bench.commands.completions.get_env_frappe_commands",
				return_value=["restore", "backup"],
			),
			patch(
				"bench.commands.completions.find_parent_bench",
				return_value=bench_dir,
			),
			patch("bench.commands.completions.get_env_cmd", return_value="python"),
			patch("bench.commands.completions._get_frappe_spec_batch", return_value=None),
			patch("bench.commands.completions.get_cmd_output", side_effect=fake_help),
		):
			script = generate_completion("bash", bench_command)

		self.assertIn("'__frappe__ restore') printf '%s' 0", script)
		self.assertIn("--with-public-files", script)
		self.assertIn("--with-private-files", script)
		self.assertIn("--backup-path", script)

	def test_runtime_resolves_frappe_subcommand_context(self):
		def fake_help(cmd, cwd=".", _raise=True):
			return (
				"Usage: frappe [OPTIONS] COMMAND [ARGS]...\n\n"
				"Commands:\n"
				"  restore\n"
			)

		with tempfile.TemporaryDirectory() as bench_dir:
			Path(bench_dir, "sites").mkdir()

			with (
				patch(
					"bench.commands.completions.get_env_frappe_commands",
					return_value=["restore"],
				),
				patch(
					"bench.commands.completions.find_parent_bench",
					return_value=bench_dir,
				),
				patch("bench.commands.completions.get_env_cmd", return_value="python"),
				patch("bench.commands.completions._get_frappe_spec_batch", return_value=None),
				patch("bench.commands.completions.get_cmd_output", side_effect=fake_help),
			):
				script = generate_completion("bash", bench_command)

			self.assertIn(
				'ctx="$(_bench_join_path "$_BENCH_FRAPPE_KEY" "$token")"',
				script,
			)

			with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as handle:
				handle.write(script)
				script_path = handle.name

			try:
				result = subprocess.run(
					[
						"bash",
						"-c",
						f"source {script_path} >/dev/null 2>&1 || true; "
						"COMP_WORDS=(bench restore ''); COMP_CWORD=2; "
						"_bench_collect_completion_state",
					],
					check=True,
					capture_output=True,
					text=True,
				)
			finally:
				Path(script_path).unlink(missing_ok=True)

		self.assertEqual(result.stdout.strip(), "__frappe__ restore|0")

	def test_runtime_completes_files_for_restore(self):
		def fake_help(cmd, cwd=".", _raise=True):
			if "frappe restore --help" in cmd:
				return (
					"Usage: frappe restore [OPTIONS] SQL-FILE-PATH\n\n"
					"Options:\n"
					"  --with-public-files PATH\n"
					"  --help              Show this message and exit.\n"
				)
			return (
				"Usage: frappe [OPTIONS] COMMAND [ARGS]...\n\n"
				"Options:\n"
				"  --site TEXT\n"
				"  --help      Show this message and exit.\n\n"
				"Commands:\n"
				"  restore\n"
			)

		with tempfile.TemporaryDirectory() as bench_dir:
			Path(bench_dir, "sites").mkdir()

			with (
				patch(
					"bench.commands.completions.get_env_frappe_commands",
					return_value=["restore"],
				),
				patch(
					"bench.commands.completions.find_parent_bench",
					return_value=bench_dir,
				),
				patch("bench.commands.completions.get_env_cmd", return_value="python"),
				patch("bench.commands.completions._get_frappe_spec_batch", return_value=None),
				patch("bench.commands.completions.get_cmd_output", side_effect=fake_help),
			):
				script = generate_completion("bash", bench_command)

			with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as handle:
				handle.write(script)
				script_path = handle.name

			try:
				result = subprocess.run(
					[
						"bash",
						"-c",
						f"source {script_path} >/dev/null 2>&1 || true; "
						"touch marker-restore-test; "
						"COMP_WORDS=(bench restore ''); COMP_CWORD=2; "
						"_bench_completion; "
						'printf "%s\\n" "${COMPREPLY[@]}"',
					],
					check=True,
					capture_output=True,
					text=True,
					cwd=bench_dir,
				)
			finally:
				Path(script_path).unlink(missing_ok=True)

		self.assertIn("marker-restore-test", result.stdout.splitlines())

	def test_runtime_appends_slash_to_completed_directories(self):
		def fake_help(cmd, cwd=".", _raise=True):
			if "frappe restore --help" in cmd:
				return (
					"Usage: frappe restore [OPTIONS] SQL-FILE-PATH\n\n"
					"Options:\n"
					"  --help              Show this message and exit.\n"
				)
			return (
				"Usage: frappe [OPTIONS] COMMAND [ARGS]...\n\n"
				"Commands:\n"
				"  restore\n"
			)

		with tempfile.TemporaryDirectory() as bench_dir:
			Path(bench_dir, "sites").mkdir()
			Path(bench_dir, "nested-dir").mkdir()

			with (
				patch(
					"bench.commands.completions.get_env_frappe_commands",
					return_value=["restore"],
				),
				patch(
					"bench.commands.completions.find_parent_bench",
					return_value=bench_dir,
				),
				patch("bench.commands.completions.get_env_cmd", return_value="python"),
				patch("bench.commands.completions._get_frappe_spec_batch", return_value=None),
				patch("bench.commands.completions.get_cmd_output", side_effect=fake_help),
			):
				script = generate_completion("bash", bench_command)

			with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as handle:
				handle.write(script)
				script_path = handle.name

			try:
				result = subprocess.run(
					[
						"bash",
						"-c",
						f"source {script_path} >/dev/null 2>&1 || true; "
						"COMP_WORDS=(bench restore nested); COMP_CWORD=2; "
						"COMP_WORDS+=( '' ); COMP_CWORD=2; "
						"_bench_completion; "
						'printf "%s\\n" "${COMPREPLY[@]}"',
					],
					check=True,
					capture_output=True,
					text=True,
					cwd=bench_dir,
				)
			finally:
				Path(script_path).unlink(missing_ok=True)

		self.assertIn("nested-dir/", result.stdout.splitlines())

	def test_runtime_completes_tilde_paths(self):
		def fake_help(cmd, cwd=".", _raise=True):
			if "frappe restore --help" in cmd:
				return (
					"Usage: frappe restore [OPTIONS] SQL-FILE-PATH\n\n"
					"Options:\n"
					"  --help              Show this message and exit.\n"
				)
			return (
				"Usage: frappe [OPTIONS] COMMAND [ARGS]...\n\n"
				"Commands:\n"
				"  restore\n"
			)

		with tempfile.TemporaryDirectory() as bench_dir:
			Path(bench_dir, "sites").mkdir()
			downloads = Path(bench_dir) / "downloads"
			downloads.mkdir()
			(downloads / "backup.sql.gz").write_text("x", encoding="utf-8")

			with (
				patch(
					"bench.commands.completions.get_env_frappe_commands",
					return_value=["restore"],
				),
				patch(
					"bench.commands.completions.find_parent_bench",
					return_value=bench_dir,
				),
				patch("bench.commands.completions.get_env_cmd", return_value="python"),
				patch("bench.commands.completions._get_frappe_spec_batch", return_value=None),
				patch("bench.commands.completions.get_cmd_output", side_effect=fake_help),
			):
				script = generate_completion("bash", bench_command)

			with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as handle:
				handle.write(script)
				script_path = handle.name

			try:
				result = subprocess.run(
					[
						"bash",
						"-c",
						f"source {script_path} >/dev/null 2>&1 || true; "
						"COMP_WORDS=(bench restore '~/downloads/b'); COMP_CWORD=2; "
						"COMP_WORDS+=( '' ); COMP_CWORD=2; "
						"_bench_completion; "
						'printf "%s\\n" "${COMPREPLY[@]}"',
					],
					check=True,
					capture_output=True,
					text=True,
					cwd=bench_dir,
					env={**os.environ, "HOME": bench_dir},
				)
			finally:
				Path(script_path).unlink(missing_ok=True)

		self.assertIn("~/downloads/backup.sql.gz", result.stdout.splitlines())

	def test_zsh_runtime_resolves_frappe_subcommand_context(self):
		def fake_help(cmd, cwd=".", _raise=True):
			return (
				"Usage: frappe [OPTIONS] COMMAND [ARGS]...\n\n"
				"Commands:\n"
				"  restore\n"
			)

		with tempfile.TemporaryDirectory() as bench_dir:
			Path(bench_dir, "sites").mkdir()

			with (
				patch(
					"bench.commands.completions.get_env_frappe_commands",
					return_value=["restore"],
				),
				patch(
					"bench.commands.completions.find_parent_bench",
					return_value=bench_dir,
				),
				patch("bench.commands.completions.get_env_cmd", return_value="python"),
				patch("bench.commands.completions._get_frappe_spec_batch", return_value=None),
				patch("bench.commands.completions.get_cmd_output", side_effect=fake_help),
			):
				script = generate_completion("zsh", bench_command)

			with tempfile.NamedTemporaryFile("w", suffix=".zsh", delete=False) as handle:
				handle.write(script)
				script_path = handle.name

			try:
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
			finally:
				Path(script_path).unlink(missing_ok=True)

		self.assertEqual(result.stdout.strip(), "__frappe__ restore|0")

	def test_zsh_completion_handles_partial_command_without_error(self):
		script = generate_completion("zsh", bench_command)

		with tempfile.NamedTemporaryFile("w", suffix=".zsh", delete=False) as handle:
			handle.write(script)
			script_path = handle.name

		try:
			result = _run_zsh_completion(script_path, ["bench", "rest"])
		finally:
			Path(script_path).unlink(missing_ok=True)

		self.assertNotIn("_bench_has_word", result.stderr)
		self.assertEqual(result.returncode, 0)

	def test_zsh_completion_uses_tilde_paths_end_to_end(self):
		def fake_help(cmd, cwd=".", _raise=True):
			if "frappe restore --help" in cmd:
				return (
					"Usage: frappe restore [OPTIONS] SQL-FILE-PATH\n\n"
					"Options:\n"
					"  --help              Show this message and exit.\n"
				)
			return (
				"Usage: frappe [OPTIONS] COMMAND [ARGS]...\n\n"
				"Commands:\n"
				"  restore\n"
			)

		with tempfile.TemporaryDirectory() as bench_dir:
			Path(bench_dir, "sites").mkdir()
			downloads = Path(bench_dir) / "downloads"
			downloads.mkdir()
			(downloads / "backup.sql.gz").write_text("x", encoding="utf-8")

			with (
				patch(
					"bench.commands.completions.get_env_frappe_commands",
					return_value=["restore"],
				),
				patch(
					"bench.commands.completions.find_parent_bench",
					return_value=bench_dir,
				),
				patch("bench.commands.completions.get_env_cmd", return_value="python"),
				patch("bench.commands.completions._get_frappe_spec_batch", return_value=None),
				patch("bench.commands.completions.get_cmd_output", side_effect=fake_help),
			):
				script = generate_completion("zsh", bench_command)

			with tempfile.NamedTemporaryFile("w", suffix=".zsh", delete=False) as handle:
				handle.write(script)
				script_path = handle.name

			try:
				result = _run_zsh_completion(
					script_path,
					["bench", "restore", "~/downloads/b"],
					cwd=bench_dir,
					env={**os.environ, "HOME": bench_dir},
				)
			finally:
				Path(script_path).unlink(missing_ok=True)

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
