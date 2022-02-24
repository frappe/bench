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
