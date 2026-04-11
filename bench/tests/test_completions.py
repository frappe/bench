import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from bench.commands import bench_command
from bench.commands.completions import _loader_line, generate_completion


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
			patch(
				"bench.commands.completions.get_env_frappe_commands",
				return_value=["migrate", "list-apps", "migrate"],
			),
			patch(
				"bench.commands.completions.find_parent_bench",
				return_value="/tmp/bench",
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
				],
			)

			self.assertEqual(result.exit_code, 0)
			self.assertTrue(completion_path.exists())
			self.assertTrue(rc_path.exists())
			self.assertIn(_loader_line(completion_path), rc_path.read_text())
