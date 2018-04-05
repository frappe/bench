import os

import click

from bench.util   import assign_if_empty
from bench.object import Bench

def _hook(app, bench_ = None, node = True, force = False):
    bench_ = Bench(bench_)

    bench_.hook_app(app, node = node, force = force)
    
@click.command('hook')
@click.argument('app', nargs = -1)
@click.option('-b', '--bench', 'bench_', help = 'Bench Instance.')
@click.option('--node',  is_flag = True, default = True,  help = 'Hook a Node Service to App.')
@click.option('-f', '--force', is_flag = True, default = False, help = 'Force Hook a Service to App. WARNING: Resets Everything.')
def hook(app, bench_ = None, node = True, force = False):
    """
    Hook Services to Apps.
    """
    _hook(app = app, bench_ = bench_, node = node, force = force)
