from __future__ import absolute_import

import click

from bench.hub.config import set_config

@click.group('setup')
def setup():
    """
    Setup commands for Hub
    """
    pass

@click.command('search')
@click.option('-b', '--bench',   type = str, multiple = True, help = 'Path to Bench Instance')
@click.option('-c', '--cluster', type = str, default  = None, help = 'Cluster Name')
@click.option('-n', '--node',    type = str, default  = None, help = 'Node Name')
@click.option('-p', '--port',    type = int, default  = None, help = 'Port')
def search(bench, cluster, node, port):
    """
    Setup a Search-Engine for a group of Benches.
    """
    from bench.hub.setup import search
    search()

setup.add_command(search)

@click.command('production')
def production():
    """
    Setup Hub for production.
    """
    pass