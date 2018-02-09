import click

@click.group('setup')
def setup():
    """
    Setup Commands for Hub
    """
    pass

@click.command('search')
@click.option('-b', '--bench', type = str, multiple = True, help = 'Path to Bench Instance')
def search():
    """
    Setup a Search-Engine for a group of Benches.
    """
    pass

setup.add_command(search)