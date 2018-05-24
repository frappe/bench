import click, subprocess, sys
from semantic_version import Version
from distutils.spawn import find_executable

def execute(bench_path):
	expected_node_ver = Version('5.0.0')
	node_exec = find_executable('node') or find_executable('nodejs')


	if node_exec:
		result = subprocess.check_output([node_exec, '-v']).decode()
	else:
		click.echo('''
		No node executable was found on your machine.
		Please install latest node version before running "bench update". For installation instructions
		please refer "Debian and Ubuntu based Linux distributions" section or "Enterprise Linux and
		Fedora" section depending upon your OS on the following link,
		"https://nodejs.org/en/download/package-manager/"
		''')
		sys.exit(1)

	node_ver = Version(result.rstrip('\n').lstrip('v'))

	if node_ver < expected_node_ver:
		click.echo('''
		Please update node to latest version before running "bench update".
		Please install latest node version before running "bench update". For installation instructions
		please refer "Debian and Ubuntu based Linux distributions" section or "Enterprise Linux and
		Fedora" section depending upon your OS on the following link,
		"https://nodejs.org/en/download/package-manager/"
		''')
		sys.exit(1)
