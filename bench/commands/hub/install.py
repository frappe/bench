import platform
import logging
import click

from bench.hub.install import brew_install

log = logging.getLogger(__name__)

@click.group('install')
def install():
    """
    Install dependencies for hubmarket.org
    """
    pass

@click.command('elasticsearch')
@click.option('--upgrade', is_flag = True, default = False, help = 'Upgrade elasticsearch')
@click.option('--with-logstash', 'logstash', help  = 'Install Logstash')
@click.option('--with-kibana',   'kibana',   help  = 'Install Kibana')
@click.option('--verbose', is_flag = True, default = True,  help = 'Display a verbose output')
def elasticsearch(upgrade = False, logstash = False, kibana = False, verbose = True):
    """
    Install elasticsearch
    """
    system = platform.system()
    if system == 'Darwin':
        brew_install(filter(None, [
            'elasticsearch',
            'logstash' if logstash else None,
            'kibana'   if kibana   else None
        ]), upgrade = upgrade, verbose = verbose)
    else:
        raise NotImplementedError

install.add_command(elasticsearch)