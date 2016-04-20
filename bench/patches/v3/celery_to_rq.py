import click, os
from bench.config.procfile import setup_procfile
from bench.config.supervisor import generate_supervisor_config

def execute(bench_path):
	click.confirm('\nThis update will remove Celery config and prepare the bench to use Python RQ.\n'
		'And it will overwrite Procfile and supervisor.conf.\n'
		'If you don\'t know what this means, type Y ;)\n\n'
		'Do you want to continue?',
		abort=True)

	setup_procfile(bench_path, force=True)

	# if production setup
	if os.path.exists(os.path.join(bench_path, 'config', 'supervisor.conf')):
		generate_supervisor_config(bench_path, force=True)
