import click

@click.group('install')
def install():
    """
    Install Dependencies for hubmarket.org
    """
    pass

@click.command('elasticsearch')
def elasticsearch():
    """
    Install elasticsearch
    """
    raise NotImplementedError

install.add_command(elasticsearch)