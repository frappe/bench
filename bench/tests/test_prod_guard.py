import unittest
from unittest.mock import patch

from bench.utils import prod_guard
from bench.utils.prod_guard import (
	MANAGED_CONFIG_KEY,
	MANAGED_ENV_VAR,
	SKIP_ENV_VAR,
	confirm_if_managed,
	get_guard_reason,
	is_managed_bench,
)

MANAGED = {MANAGED_CONFIG_KEY: True}


class TestIsManagedBench(unittest.TestCase):
	def setUp(self):
		patcher = patch.dict("os.environ", {}, clear=True)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_managed_via_config(self):
		self.assertTrue(is_managed_bench(MANAGED))

	def test_managed_via_env(self):
		with patch.dict("os.environ", {MANAGED_ENV_VAR: "1"}):
			self.assertTrue(is_managed_bench({}))

	def test_unmanaged(self):
		self.assertFalse(is_managed_bench({}))
		self.assertFalse(is_managed_bench({"monitor": True}))
		self.assertFalse(is_managed_bench({MANAGED_CONFIG_KEY: False}))


class TestGuardReason(unittest.TestCase):
	def test_guarded_commands(self):
		for command in ("install-app", "drop-site", "set-config", "get-app", "update"):
			with self.subTest(command=command):
				self.assertIsNotNone(get_guard_reason(command))

	def test_unguarded_commands(self):
		for command in ("backup", "clear-cache", "console", "mariadb", "doctor", "build"):
			with self.subTest(command=command):
				self.assertIsNone(get_guard_reason(command))

	def test_every_command_explains_its_desync(self):
		for command, reason in prod_guard.GUARDED_COMMANDS.items():
			with self.subTest(command=command):
				self.assertIsInstance(reason, str)
				# implicit concatenation across wrapped lines drops spaces easily
				self.assertEqual(reason, " ".join(reason.split()))


class TestConfirmIfManaged(unittest.TestCase):
	"""The guard only prompts for a guarded command, on a managed bench, at a TTY."""

	def setUp(self):
		env = patch.dict("os.environ", {}, clear=True)
		env.start()
		self.addCleanup(env.stop)

		argv = patch.object(prod_guard.sys, "argv", ["bench", "install-app", "erpnext"])
		argv.start()
		self.addCleanup(argv.stop)

		tty = patch.object(prod_guard.sys.stdin, "isatty", return_value=True)
		tty.start()
		self.addCleanup(tty.stop)

		self.confirm = patch.object(prod_guard.click, "confirm", return_value=False).start()
		self.addCleanup(patch.stopall)

	def assert_did_not_prompt(self, *args, **kwargs):
		confirm_if_managed(*args, **kwargs)
		self.confirm.assert_not_called()

	def test_aborts_when_declined(self):
		with self.assertRaises(SystemExit) as cm:
			confirm_if_managed("install-app", MANAGED)

		self.assertNotEqual(cm.exception.code, 0)
		self.confirm.assert_called_once()

	def test_proceeds_when_accepted(self):
		self.confirm.return_value = True
		confirm_if_managed("install-app", MANAGED)
		self.confirm.assert_called_once()

	def test_aborts_when_prompt_is_interrupted(self):
		self.confirm.side_effect = prod_guard.click.Abort()
		with self.assertRaises(SystemExit):
			confirm_if_managed("install-app", MANAGED)

	def test_silent_on_unmanaged_bench(self):
		self.assert_did_not_prompt("install-app", {})

	def test_silent_for_unguarded_command(self):
		self.assert_did_not_prompt("backup", MANAGED)

	def test_silent_without_a_command(self):
		self.assert_did_not_prompt(None, MANAGED)

	def test_silent_when_not_a_tty(self):
		"""The agent drives benches over `docker exec` without a TTY."""
		with patch.object(prod_guard.sys.stdin, "isatty", return_value=False):
			self.assert_did_not_prompt("install-app", MANAGED)

	def test_silent_when_bypass_is_set(self):
		with patch.dict("os.environ", {SKIP_ENV_VAR: "1"}):
			self.assert_did_not_prompt("install-app", MANAGED)

	def test_silent_for_help(self):
		for flag in ("--help", "-h"):
			with self.subTest(flag=flag):
				self.confirm.reset_mock()
				with patch.object(prod_guard.sys, "argv", ["bench", "install-app", flag]):
					self.assert_did_not_prompt("install-app", MANAGED)


if __name__ == "__main__":
	unittest.main()
