from __future__ import absolute_import

import os
import os.path as osp
import json
import logging

import click

from bench.system import popen
from bench.util   import assign_if_empty, sequencify

log = logging.getLogger(__name__)

# TODO: bench.TREE
TREE = dict(
    apps   = None,
    sites  = None,
    env    = None,
    config = None,
    logs   = None
)

# TODO: bench._has_app
def _has_app(path, app, installed = False):
    # Assumes that it's gone through previous Bench checks.
    path = osp.abspath(path)
    papp = osp.join(path, 'apps', app)

    if osp.exists(papp):
        if installed:
            pip = osp.join(path, 'env', 'bin', 'pip')
            code, _, _ = popen('{pip} show {app}'.format(
                pip = pip, app = app
            ), output = True)
            
            if code == 0:
                return True
            else:
                return False
                
        return True

    return False

def _check_bench(path, raise_err = True):
    """
    check if path is a bench instance.
    """
    path = osp.abspath(path)
    err  = '{path} not a valid Bench instance.'.format(path = path)

    if not osp.exists(path):
        if raise_err:
            raise ValueError('{path} does not exist.'.format(
                path = path
            ))
        else:
            return False
    else:
        # Check if bare minimum folders exists.
        for folder in list(TREE): # bench tree depth = 1
            fpath = osp.join(path, folder)
            if not osp.exists(fpath):
                if raise_err:
                    raise ValueError(err)
                else:
                    return False

        # Check if Frappe is installed.
        if not _has_app(path, 'frappe', installed = True):
            if raise_err:
                raise ValueError(err)
            else:
                return False
        
    return True

def _check_app(path, raise_err = False):
    """
    check if path is a valid Frappe App.
    """
    # TODO: Lol, let's check requirements?
    # STUB
    return True

class App(object):
    def __init__(self, path):
        _check_app(path, raise_err = True)

        self.path = path
        self.name = osp.basename(path)

    def hook(node = True):
        if node:
            pass

    def __repr__(self):
        return '<App {name}>'.format(name = self.name)

class Bench(object):
    def __init__(self, path):
        _check_bench(path, raise_err = True)

        self.path = path
        self.name = osp.basename(path)

    def has_app(self, app, installed = False):
        return _has_app(
            path      = self.path,
            app       = app,
            installed = installed
        )

    def get_app(self, app = None, install = False, raise_err = True):
        path = osp.join(self.path, 'apps')

        if not app:
            for app in os.listdir(path):
                abspath = osp.join(path, app)
        else:
            apps  = sequencify(app)
            apps_ = [ ]

            for app in apps:
                if self.has_app(app):
                    papp = osp.join(path, app)
                    app_ = App(papp)
                    print(app_)

    def hook_app(self, app = None, node = True, raise_err = True):
        app = self.get_app(app, raise_err = raise_err)
        
    def __repr__(self):
        return '<Bench {name}>'.format(name = self.name)

def _hook(app, bench_ = None, node = True):
    bench_ = assign_if_empty(bench_, os.getcwd())
    bench_ = Bench(bench_)

    bench_.hook_app(app, node = node)
    
@click.command('hook')
@click.argument('app')
@click.option('--bench', 'bench_', help = 'Bench Instance.')
@click.option('--node',  is_flag = True, default = True, help = 'Hook a Node Service to App.')
def hook(app, bench_ = None, node = True):
    """
    Hook Services to Apps.
    """
    _hook(app = app, bench_ = bench_, node = node)
