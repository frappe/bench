import unittest
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bench.commands.ai import bench_ai


class TestBenchAiCommand(unittest.TestCase):
	def test_dry_run_skips_api(self):
		with patch("bench.commands.ai.requests.post") as post:
			runner = CliRunner()
			result = runner.invoke(bench_ai, ["backup all sites", "--dry-run"])
			self.assertEqual(result.exit_code, 0, msg=result.output)
			post.assert_not_called()
			self.assertIn("Context size", result.output)
			self.assertIn("Model", result.output)
			self.assertIn("dry run", result.output.lower())

	def test_missing_api_key(self):
		# CliRunner may merge with the parent process env; patch ensures no key is seen.
		with patch("bench.commands.ai.get_api_key", return_value=None):
			runner = CliRunner()
			result = runner.invoke(bench_ai, ["hello"])
		self.assertNotEqual(result.exit_code, 0)
		self.assertIn("Missing API key", result.output)

	def test_suggestion_with_mocked_completion(self):
		def fake_post(url, headers=None, json=None, timeout=None):
			r = MagicMock()
			r.status_code = 200
			r.json.return_value = {
				"choices": [
					{
						"message": {
							"content": "Back up every site.\n```bash\nbench backup-all-sites\n```"
						}
					}
				]
			}
			r.raise_for_status = MagicMock()
			return r

		with patch("bench.commands.ai.requests.post", side_effect=fake_post):
			runner = CliRunner()
			result = runner.invoke(
				bench_ai,
				["backup everything"],
				env={"BENCH_AI_API_KEY": "test-secret"},
			)
		self.assertEqual(result.exit_code, 0, msg=result.output)
		self.assertIn("bench backup-all-sites", result.output)
		self.assertIn("Guidance", result.output)
		self.assertIn("Suggested command", result.output)
		self.assertIn("OK —", result.output)

	def test_validate_bench_native_known_command(self):
		from bench.commands import bench_command
		from bench.commands.ai import validate_suggested_command_line

		ok, _ = validate_suggested_command_line(
			"bench get-app erpnext https://github.com/frappe/erpnext",
			bench_command,
			None,
		)
		self.assertTrue(ok)

	def test_validate_bench_native_unknown_command(self):
		from bench.commands import bench_command
		from bench.commands.ai import validate_suggested_command_line

		ok, msg = validate_suggested_command_line(
			"bench this-is-not-a-real-subcommand-xyz",
			bench_command,
			None,
		)
		self.assertFalse(ok)
		self.assertIn("Unknown", msg)

	def test_validate_frappe_when_list_provided(self):
		from bench.commands import bench_command
		from bench.commands.ai import validate_suggested_command_line

		ok, _ = validate_suggested_command_line(
			"bench --site foo.local migrate",
			bench_command,
			{"migrate", "backup"},
		)
		self.assertTrue(ok)
		ok2, _ = validate_suggested_command_line(
			"bench doctor",
			bench_command,
			{"doctor", "migrate"},
		)
		self.assertTrue(ok2)
		bad, msg = validate_suggested_command_line(
			"bench --site foo.local totally-fake-frappe-cmd",
			bench_command,
			{"migrate", "backup"},
		)
		self.assertFalse(bad)
		self.assertIn("Unknown framework", msg)

	def test_parse_suggested_command_prefers_runnable_line(self):
		from bench.commands.ai import parse_suggested_command

		text = """### Command
```bash
bench get-app <app> <repo-url>
```
```bash
bench get-app erpnext https://github.com/frappe/erpnext
```
"""
		self.assertEqual(
			parse_suggested_command(text),
			"bench get-app erpnext https://github.com/frappe/erpnext",
		)

	def test_parse_suggested_command_ignores_prose(self):
		from bench.commands.ai import parse_suggested_command

		text = (
			"### Summary\nThe command `bench doctor` is not listed.\n"
			"Visit https://example.com for more.\n"
		)
		self.assertEqual(parse_suggested_command(text), "")

	def test_parse_suggested_command_markdown_list_line(self):
		from bench.commands.ai import parse_suggested_command

		text = "### Command\n- bench doctor\n"
		self.assertEqual(parse_suggested_command(text), "bench doctor")

	def test_crib_allows_doctor_without_frappe_env(self):
		from bench.commands import bench_command
		from bench.commands.ai import validate_suggested_command_line

		ok, _ = validate_suggested_command_line("bench doctor", bench_command, None)
		self.assertTrue(ok)

	def test_collect_bench_click_paths_includes_nested(self):
		from bench.commands import bench_command
		from bench.commands.ai import collect_bench_click_paths

		paths = set(collect_bench_click_paths(bench_command))
		self.assertIn("get-app", paths)
		self.assertTrue(any(p.startswith("setup ") for p in paths))

	def test_normalize_base_url(self):
		from bench.commands.ai import normalize_base_url

		self.assertEqual(
			normalize_base_url("https://example.com"),
			"https://example.com/v1",
		)
		self.assertEqual(
			normalize_base_url("https://example.com/v1"),
			"https://example.com/v1",
		)
		self.assertEqual(
			normalize_base_url("https://example.com/v1/"),
			"https://example.com/v1",
		)


if __name__ == "__main__":
	unittest.main()
