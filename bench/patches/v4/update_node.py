import click, subprocess, sys
from semantic_version import Version

def execute(bench_path):
    expected_node_ver = Version('5.0.0')

    result = subprocess.check_output(['node', '-v'])
    node_ver = Version(result.rstrip('\n').lstrip('v'))

    if node_ver < expected_node_ver:
        click.echo('\nPlease update node version to 5.x before running the "bench update"\n\n')
        sys.exit(1)
