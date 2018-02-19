import subprocess

def execute(bench_path):
	subprocess.check_output(['sudo', 'npm', 'install', '-g', 'yarn'])