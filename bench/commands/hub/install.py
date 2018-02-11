import platform
import logging
import click

from bench.hub.install import brew_install

log = logging.getLogger(__name__)

@click.group('install')
def install():
    """
    Install dependencies for Hub
    """
    pass

@click.command('elasticsearch')
@click.option('--upgrade', is_flag = True, default = False,  help = 'Upgrade elasticsearch')
@click.option('--with-logstash', 'logstash', is_flag = True, default = True,  help = 'Install Logstash')
@click.option('--with-kibana',   'kibana',   is_flag = True, default = False, help = 'Install Kibana')
@click.option('--quiet',   is_flag = True, default = False,  help = 'Display a verbose output')
def elasticsearch(upgrade = False, logstash = True, kibana = False, quiet = False):
    """
    Install elasticsearch
    """
    system = platform.system()
    if system == 'Darwin':
        brew_install(filter(None, [
            'elasticsearch',
            'logstash' if logstash else None,
            'kibana'   if kibana   else None
        ]), update = True, upgrade = upgrade, verbose = not quiet)
    else:
        raise NotImplementedError

install.add_command(elasticsearch)