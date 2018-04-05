import click

from bench.object import Bench

def _link(app, bench_ = None, force = False, onto = None):
    bench_ = Bench(bench_)
    bench_.link_app(app, force = force, onto = onto)

@click.command('link')
@click.argument('app', nargs = -1)
@click.option('-b', '--bench', 'bench_', help = 'Bench Instance.')
@click.option('-f', '--force', is_flag = True, default = False, help = 'Force relink.')
@click.option('-o', '--onto',  multiple = True, help = 'Link App onto Another.')
def link(app, bench_ = None, force = False, onto = None):
    """
    Link a Frappe Node app.
    """
    _link(app, bench_ = bench_, force = force, onto = onto)