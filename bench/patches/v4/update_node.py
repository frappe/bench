import click, subprocess, sys
from semantic_version import Version
from distutils.spawn import find_executable

def execute(bench_path):
    expected_node_ver = Version('5.0.0')
    node_exec = find_executable('node')

    if node_exec:
        result = subprocess.check_output([node_exec, '-v'])
    else:
        click.echo('\nNo node executable was found on your machine.\nPlease install node 5.x before\n'
        'running "bench update".\nInstallation instructions for CentOS and Ubuntu can be found on \n'
        'the following link,\n'
        '"https://www.metachris.com/2015/10/how-to-install-nodejs-5-on-centos-and-ubuntu/"\n\n')
        sys.exit(1)

    node_ver = Version(result.rstrip('\n').lstrip('v'))

    if node_ver < expected_node_ver:
        click.echo('''Please update node version to 5.x before running "bench update".
        'Installation instructions for CentOS and Ubuntu can be found on the following link,
        '"https://www.metachris.com/2015/10/how-to-install-nodejs-5-on-centos-and-ubuntu/"

		''')
        sys.exit(1)
