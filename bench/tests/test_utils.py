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

	def test_new_app_title(self):
		args = self._make_app_args("my_app", title="My App")
		self.assertIn("--title", args)
		self.assertEqual(args[args.index("--title") + 1], "My App")

	def test_new_app_description(self):
		args = self._make_app_args("my_app", description="A great app")
		self.assertIn("--description", args)
		self.assertEqual(args[args.index("--description") + 1], "A great app")

	def test_new_app_publisher(self):
		args = self._make_app_args("my_app", publisher="ACME Corp")
		self.assertIn("--publisher", args)
		self.assertEqual(args[args.index("--publisher") + 1], "ACME Corp")

	def test_new_app_email(self):
		args = self._make_app_args("my_app", email="dev@example.com")
		self.assertIn("--email", args)
		self.assertEqual(args[args.index("--email") + 1], "dev@example.com")

	def test_new_app_license(self):
		args = self._make_app_args("my_app", license="mit")
		self.assertIn("--license", args)
		self.assertEqual(args[args.index("--license") + 1], "mit")

	def test_new_app_create_github_workflow_flag(self):
		args = self._make_app_args("my_app", github_workflow=True)
		self.assertIn("--github-workflow", args)

	def test_new_app_create_github_workflow_false_flag(self):
		args = self._make_app_args("my_app", github_workflow=False)
		self.assertIn("--no-github-workflow", args)

	def test_new_app_create_github_workflow_omitted_by_default(self):
		args = self._make_app_args("my_app")
		self.assertNotIn("--github-workflow", args)
		self.assertNotIn("--no-github-workflow", args)

	def test_new_app_create_frontend_flag(self):
		args = self._make_app_args("my_app", frontend=True)
		self.assertIn("--frontend", args)

	def test_new_app_create_frontend_false_flag(self):
		args = self._make_app_args("my_app", frontend=False)
		self.assertIn("--no-frontend", args)

	def test_new_app_frontend_route(self):
		args = self._make_app_args("my_app", route="m")
		self.assertIn("--route", args)
		self.assertEqual(args[args.index("--route") + 1], "m")

	def test_new_app_branch_name(self):
		args = self._make_app_args("my_app", branch="main")
		self.assertIn("--branch", args)
		self.assertEqual(args[args.index("--branch") + 1], "main")

	def test_new_app_all_options_combined(self):
		args = self._make_app_args(
			"my_app",
			title="My App",
			description="A great app",
			publisher="ACME Corp",
			email="dev@example.com",
			license="mit",
			github_workflow=True,
			frontend=True,
			route="m",
			branch="main",
		)
		for flag, value in (
			("--title", "My App"),
			("--description", "A great app"),
			("--publisher", "ACME Corp"),
			("--email", "dev@example.com"),
			("--license", "mit"),
			("--route", "m"),
			("--branch", "main"),
		):
			self.assertIn(flag, args)
			self.assertEqual(args[args.index(flag) + 1], value)
		self.assertIn("--github-workflow", args)
		self.assertIn("--frontend", args)

	def test_new_app_cli_options_defined(self):
		"""The new-app click command exposes all expected options."""
		from click.testing import CliRunner
		from bench.commands.make import new_app as new_app_cmd

		runner = CliRunner()
		result = runner.invoke(new_app_cmd, ["--help"])
		help_text = result.output

		for option in (
			"--title",
			"--description",
			"--publisher",
			"--email",
			"--license",
			"--github-workflow",
			"--no-github-workflow",
			"--frontend",
			"--no-frontend",
			"--route",
			"--branch",
			"--no-git",
		):
			self.assertIn(option, help_text, f"Expected '{option}' in --help output")
