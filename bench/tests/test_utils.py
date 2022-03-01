import unittest

from bench.app import App
from bench.bench import Bench
from bench.utils import exec_cmd


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
					app.is_url == True,
					app.on_disk == False,
					app.org == "frappe",
					app.url == git_url,
				]
			)
		)

	def test_get_required_deps_url(self):
		self.assertEqual(
			get_required_deps_url(git_url="https://github.com/frappe/frappe.git", branch=None, repo_name="frappe"),
			"https://raw.github.com/frappe/frappe/develop/frappe/hooks.py",
		)
		self.assertEqual(
			get_required_deps_url(
				git_url="https://github.com/frappe/frappe.git", branch="version-13", repo_name="frappe"
			),
			"https://raw.github.com/frappe/frappe/version-13/frappe/hooks.py",
		)

	def test_is_valid_frappe_branch(self):
		self.assertTrue(is_valid_frappe_branch("https://github.com/frappe/frappe", frappe_branch=""))
		self.assertTrue(is_valid_frappe_branch("https://github.com/frappe/frappe", frappe_branch="develop"))
		self.assertTrue(is_valid_frappe_branch("https://github.com/frappe/erpnext", frappe_branch="version-13"))
		self.assertFalse(is_valid_frappe_branch("https://github.com/frappe/erpnext", frappe_branch="version-1"))

