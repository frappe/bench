import click

@click.group('setup')
def setup():
    """
    Setup Commands for hubmarket.org
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
    pass

setup.add_command(search)