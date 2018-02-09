import platform
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
    system = platform.system()
    if system == 'Darwin':
        pass
    raise NotImplementedError

install.add_command(elasticsearch)