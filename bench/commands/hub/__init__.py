import click

from bench.commands.hub.install import install
from bench.commands.hub.config  import config
from bench.commands.hub.setup   import setup

@click.group('hub')
def hub():
    """
    Setup Hub
    """
    pass

hub.add_command(install)
hub.add_command(config)
hub.add_command(setup)

@click.command('init')
@click.option('-b', '--bench',  type = str, multiple = True,  help = 'Path to Bench Instances')
@click.option('-g', '--group',  type = str,  default = None,  help = 'Path to Group of Benches')
@click.option('--validate', is_flag = True, default = False,  help = 'Validate Bench Instances')
@click.option('--reinit',   is_flag = True, default = False,  help = 'Reinitialize Bench Instances for Hub.')
def init(bench = None, group = None, validate = False, reinit = False):
    """
    Initialize a Bench / Group of Benches for Hub
    """
    from bench.hub import init
    init(bench = bench, group = group, validate = validate, reinit = reinit)

hub.add_command(init)

@click.command('migrate')
def migrate():
    """
    Migrate registered Site Databases to Hub Database.
    """
    from bench.hub import migrate
    migrate()

hub.add_command(migrate)

@click.command('start')
@click.option('-d', '--daemonize', is_flag = True, help = 'Run Hub in background')
def start(daemonize = False):
    """
    Start Hub Processes
    """
    from bench.hub import start
    start(daemonize = daemonize)

hub.add_command(start)

@click.command('health')
@click.option('--verbose', is_flag = True, default = False, help = 'Display a verbose output')
def health(verbose = False):
    """
    Display current Hub Cluster / Server Node information.
    """
    from bench.hub.health import health
    health(verbose = verbose)

@click.command('doctor')
@click.option('--force', is_flag = True, default = False, help = 'Force Healing (Force Stop / Restart Processes).')
def doctor(force = False):
    """
    Diagnose and Heal Hub issues.
    """
    from bench.hub.health import doctor
    doctor(force = force)

hub.add_command(doctor)