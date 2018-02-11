import platform
import logging
import click

from bench.hub.util import popen, which

log = logging.getLogger(__name__)

@click.group('install')
def install():
    """
    Install dependencies for hubmarket.org
    """
    pass

@click.command('elasticsearch')
def elasticsearch():
    """
    Install elasticsearch
    """
    system = platform.system()
    if system == 'Darwin':
        brew = which('brew')
        if not brew:
            log.info('Installing HomeBrew')
            popen('{ruby} -e "$({curl} -sL https://git.io/get-brew)"'.format(
                curl = which('curl', raise_err = True),
                ruby = which('ruby', raise_err = True)
            ))
        
        brew = which('brew', raise_err = True)
        popen('{brew} install elasticsearch'.format(brew = brew), output = True)
    else:
        raise NotImplementedError

install.add_command(elasticsearch)