import click

def _hook(app, bench = None, node = False):
    bench = Bench(bench) 

@click.command('hook')
@click.argument('app')
@click.option('--bench', help = 'Bench Instance.')
@click.option('--node',  is_flag = True, default = True, help = 'Hook a Node Service to App.')
def hook(app, bench = None, node = True):
    """
    Hook Services to Apps.
    """
    _hook(app = app, bench = bench, node = node)