# imports - standard imports
import subprocess

# imports - module imports
from bench.utils import log, get_cmd_output, exec_cmd
from bench.cli import change_uid_msg


def execute(bench_path):
	"""fix supervisor using root then remove bench sudo later
	chronology samajhiye"""
	cmd = ["sudo", "-n", "bench"]
	is_bench_sudoers_set = (not subprocess.call(cmd)) or (change_uid_msg in get_cmd_output(cmd))

	if is_bench_sudoers_set:
		exec_cmd("sudo bench setup supervisor --yes")
		exec_cmd("sudo bench setup sudoers")
