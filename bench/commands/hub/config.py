import click

from bench.hub.config import set_config

@click.command('config')
@click.argument('key')
@click.argument('value')
def config(key, value):
    """
    Set Hub Config
    """
    set_config(key, value)