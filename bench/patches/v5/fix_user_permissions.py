# imports - standard imports
import subprocess
import sys

# imports - module imports
from bench.utils import get_cmd_output, exec_cmd, which
from bench.cli import change_uid_msg


def execute(bench_path):
	cmd = ["sudo", "-n", "bench"]

	is_bench_sudoers_set = (not subprocess.call(cmd)) or (change_uid_msg in get_cmd_output(cmd))
	is_supervisor_installed = which('supervisorctl')

	if not is_supervisor_installed:
		exec_cmd("{} -m pip install supervisor".format(sys.executable))

	if is_bench_sudoers_set:
		exec_cmd("sudo bench setup supervisor --yes")
		exec_cmd("sudo bench setup sudoers")
