import subprocess

def execute(bench_path):
	subprocess.check_output(['env/bin/pip', 'install', '--upgrade', 'dropbox'], cwd=bench_path)