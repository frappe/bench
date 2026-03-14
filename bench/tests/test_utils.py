import os
import shutil
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from bench.app import App
from bench.bench import Bench
from bench.exceptions import InvalidRemoteException
from bench.utils import is_valid_frappe_branch


class TestUtils(unittest.TestCase):
	def test_app_utils(self):
		git_url = "https://github.com/frappe/frappe"
		branch = "develop"
		app = App(name=git_url, branch=branch, bench=Bench("."))
		self.assertTrue(
			all(
				[
					app.name == git_url,
					app.branch == branch,
					app.tag == branch,
					app.is_url is True,
					app.on_disk is False,
					app.org == "frappe",
					app.url == git_url,
				]
			)
		)

	def test_is_valid_frappe_branch(self):
		with self.assertRaises(InvalidRemoteException):
			is_valid_frappe_branch(
				"https://github.com/frappe/frappe.git", frappe_branch="random-branch"
			)
			is_valid_frappe_branch(
				"https://github.com/random/random.git", frappe_branch="random-branch"
			)

		is_valid_frappe_branch(
			"https://github.com/frappe/frappe.git", frappe_branch="develop"
		)
		is_valid_frappe_branch(
			"https://github.com/frappe/frappe.git", frappe_branch="v13.29.0"
		)

	def test_app_states(self):
		bench_dir = "./sandbox"
		sites_dir = os.path.join(bench_dir, "sites")

		if not os.path.exists(sites_dir):
			os.makedirs(sites_dir)

		fake_bench = Bench(bench_dir)

		self.assertTrue(hasattr(fake_bench.apps, "states"))

		fake_bench.apps.states = {
			"frappe": {
				"resolution": {"branch": "develop", "commit_hash": "234rwefd"},
				"version": "14.0.0-dev",
			}
		}
		fake_bench.apps.update_apps_states()

		self.assertEqual(fake_bench.apps.states, {})

		frappe_path = os.path.join(bench_dir, "apps", "frappe")

		os.makedirs(os.path.join(frappe_path, "frappe"))

		subprocess.run(["git", "init"], cwd=frappe_path, capture_output=True, check=True)

		with open(os.path.join(frappe_path, "frappe", "__init__.py"), "w+") as f:
			f.write("__version__ = '11.0'")

		subprocess.run(["git", "add", "."], cwd=frappe_path, capture_output=True, check=True)
		subprocess.run(
			["git", "config", "user.email", "bench-test_app_states@gha.com"],
			cwd=frappe_path,
			capture_output=True,
			check=True,
		)
		subprocess.run(
			["git", "config", "user.name", "App States Test"],
			cwd=frappe_path,
			capture_output=True,
			check=True,
		)
		subprocess.run(
			["git", "commit", "-m", "temp"], cwd=frappe_path, capture_output=True, check=True
		)

		fake_bench.apps.update_apps_states(app_name="frappe")

		self.assertIn("frappe", fake_bench.apps.states)
		self.assertIn("version", fake_bench.apps.states["frappe"])
		self.assertEqual("11.0", fake_bench.apps.states["frappe"]["version"])

		shutil.rmtree(bench_dir)

	def test_ssh_ports(self):
		app = App("git@github.com:22:frappe/frappe")
		self.assertEqual(
			(app.use_ssh, app.org, app.repo, app.app_name), (True, "frappe", "frappe", "frappe")
		)


class TestNewAppCommand(unittest.TestCase):
	"""Tests for the bench new-app command options and argument construction."""

	def _make_app_args(self, app, **kwargs):
		"""Call new_app() with mocked run_frappe_cmd and install_app, return captured args."""
		captured = {}

		def mock_run_frappe_cmd(*args, **kw):
			captured["args"] = list(args)

		with (
			patch("bench.app.bench") as mock_bench,
			patch("bench.app.run_frappe_cmd", side_effect=mock_run_frappe_cmd),
			patch("bench.app.install_app"),
			patch("bench.app.logger"),
		):
			mock_bench.FRAPPE_VERSION = 15
			from bench.app import new_app

			new_app(app, bench_path="/tmp/fake-bench", **kwargs)

		return captured.get("args", [])

	def test_new_app_basic_args(self):
		"""make-app receives the apps directory and app name."""
		args = self._make_app_args("my_app")
		self.assertEqual(args[0], "make-app")
		self.assertTrue(args[1].endswith("/apps"))
		self.assertEqual(args[2], "my_app")

	def test_new_app_no_extra_args_by_default(self):
		"""No extra args are added when no options are passed."""
		args = self._make_app_args("my_app")
		self.assertEqual(len(args), 3)
		self.assertEqual(args[0], "make-app")
		self.assertEqual(args[2], "my_app")

	def test_new_app_app_title(self):
		args = self._make_app_args("my_app", app_title="My App")
		self.assertIn("--app-title", args)
		self.assertEqual(args[args.index("--app-title") + 1], "My App")

	def test_new_app_app_description(self):
		args = self._make_app_args("my_app", app_description="A great app")
		self.assertIn("--app-description", args)
		self.assertEqual(args[args.index("--app-description") + 1], "A great app")

	def test_new_app_app_publisher(self):
		args = self._make_app_args("my_app", app_publisher="ACME Corp")
		self.assertIn("--app-publisher", args)
		self.assertEqual(args[args.index("--app-publisher") + 1], "ACME Corp")

	def test_new_app_app_email(self):
		args = self._make_app_args("my_app", app_email="dev@example.com")
		self.assertIn("--app-email", args)
		self.assertEqual(args[args.index("--app-email") + 1], "dev@example.com")

	def test_new_app_app_license(self):
		args = self._make_app_args("my_app", app_license="mit")
		self.assertIn("--app-license", args)
		self.assertEqual(args[args.index("--app-license") + 1], "mit")

	def test_new_app_create_github_workflow_flag(self):
		args = self._make_app_args("my_app", create_github_workflow=True)
		self.assertIn("--create-github-workflow", args)

	def test_new_app_create_github_workflow_not_added_by_default(self):
		args = self._make_app_args("my_app", create_github_workflow=False)
		self.assertNotIn("--create-github-workflow", args)

	def test_new_app_branch_name(self):
		args = self._make_app_args("my_app", branch_name="main")
		self.assertIn("--branch-name", args)
		self.assertEqual(args[args.index("--branch-name") + 1], "main")

	def test_new_app_all_options_combined(self):
		args = self._make_app_args(
			"my_app",
			app_title="My App",
			app_description="A great app",
			app_publisher="ACME Corp",
			app_email="dev@example.com",
			app_license="mit",
			create_github_workflow=True,
			branch_name="main",
		)
		for flag, value in (
			("--app-title", "My App"),
			("--app-description", "A great app"),
			("--app-publisher", "ACME Corp"),
			("--app-email", "dev@example.com"),
			("--app-license", "mit"),
			("--branch-name", "main"),
		):
			self.assertIn(flag, args)
			self.assertEqual(args[args.index(flag) + 1], value)
		self.assertIn("--create-github-workflow", args)

	def test_new_app_cli_options_defined(self):
		"""The new-app click command exposes all expected options."""
		from click.testing import CliRunner
		from bench.commands.make import new_app as new_app_cmd

		runner = CliRunner()
		result = runner.invoke(new_app_cmd, ["--help"])
		help_text = result.output

		for option in (
			"--app-title",
			"--app-description",
			"--app-publisher",
			"--app-email",
			"--app-license",
			"--create-github-workflow",
			"--branch-name",
			"--no-git",
		):
			self.assertIn(option, help_text, f"Expected '{option}' in --help output")
