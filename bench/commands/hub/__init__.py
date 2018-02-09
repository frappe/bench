import click

from bench.commands.hub.install import install
from bench.commands.hub.setup   import setup

@click.group('hub')
def hub():
    """
    Setup Bench for hubmarket.org
    """
    pass

hub.add_command(install)
hub.add_command(setup)