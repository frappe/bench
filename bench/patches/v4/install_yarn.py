import os
from bench.utils import exec_cmd

def execute(bench_path):
	exec_cmd('npm install yarn', os.path.join(bench_path, 'apps/frappe'))
