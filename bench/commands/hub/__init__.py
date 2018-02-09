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

@click.command('init')
@click.option('-b', '--bench', type = str, multiple = True,  help = 'Path to Bench Instances')
@click.option('-g', '--group', type = str,  default = None,  help = 'Path to Group of Benches')
@click.option('--validate', is_flag = True, default = False, help = 'Validate Bench Instances')
def init(bench = None, group = None, validate = False):
    """
    Initialize a Bench / Group of Benches for hubmarket.org
    """
    from bench.hub import init
    init(bench = bench, group = group, validate = validate)

hub.add_command(init)

@click.command('start')
@click.option('-d', '--daemonize', is_flag = True, help = 'Run Hub in background.')
def start(daemonize = False):
    """
    Start the Hub Processes
    """
    from bench.hub import start
    start(daemonize = daemonize)

hub.add_command(start)