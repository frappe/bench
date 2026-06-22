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


class TestBenchCompletionGeneration(unittest.TestCase):
	def test_bash_completion_is_shell_only(self):
		script = generate_completion("bash", bench_command)

		self.assertIn("_bench_subcommands_for()", script)
		self.assertIn("complete -o nosort -F _bench_completion bench", script)
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

	def test_zsh_completion_bootstraps_bash_compat(self):
		script = generate_completion("zsh", bench_command)

		self.assertIn("#compdef bench", script)
		self.assertIn("autoload -U bashcompinit", script)
		self.assertIn("complete -o nosort -F _bench_completion bench", script)

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
