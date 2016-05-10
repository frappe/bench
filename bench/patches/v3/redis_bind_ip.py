import click
from bench.config.redis import generate_config

def execute(bench_path):
	click.confirm('\nThis update will replace ERPNext\'s Redis configuration files to fix a major security issue.\n'
		'If you don\'t know what this means, type Y ;)\n\n'
		'Do you want to continue?',
		abort=True)

	generate_config(bench_path)
