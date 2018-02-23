from __future__ import absolute_import

import os
import os.path as osp
import json
import logging

import click

from bench.system import makedirs, popen, which
from bench.util   import assign_if_empty, sequencify

log = logging.getLogger(__name__)
log.setLevel(logging.CRITICAL)

TEMPLATE_NODE_INDEX   = \
"""
// Frappe-Node
// Do something awesome!
const frappe   = require("frappe");
const {app}    = {{ }};

module.exports = {app};
"""

TEMPLATE_NODE_PACKAGE = \
"""
{{
  "name": "{app}",
  "version": "0.1.0",
  "main": "index.js"
}}
"""

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
        
        pnode     = osp.join(self.path, self.name, 'node')
        if osp.exists(pnode):
            self.node = pnode
        else:
            self.node = None

    def hook(self, node = True, force = False):
        if node:
            self._hook_node(force = force)

    def link(self, force = False, onto = None):
        name   = self.name
        _, prefix, _ = popen('{npm} config get prefix'.format(npm = which('npm', raise_err = True)),
            output = True
        )
        
        source = osp.join(self.path, self.name, 'node')
        dest   = osp.join(prefix, 'lib', 'node_modules', self.name)

        create = True

        if osp.exists(dest):
            if force:
                os.remove(source)
            else:
                log.warn("App Link {dest} already exists.".format(dest = dest))
                create = False
            
        if create:
            os.symlink(source, dest)

        if onto:
            onto = sequencify(onto)
            for app in onto:
                log.info("Linking {target} to {source}".format(
                    target = self.name, source = app
                ))
                path = osp.abspath(osp.join(self.path, '..', app))
                app_ = App(path)
                
                popen('{npm} link {app}'.format(
                    npm = which('npm', raise_err = True),
                    app = self.name
                ), directory = app_.node)

    def _hook_node(self, force = False):
        if self.name != 'frappe':
            self.module = osp.join(self.path, self.name)
            pnode       = osp.join(self.module, 'node')

            makedirs(pnode, exists_ok = force)

            ppack       = osp.join(pnode, 'package.json')

            if not osp.exists(ppack) or force:
                with open(ppack, 'w') as f:
                    f.write(TEMPLATE_NODE_PACKAGE.format(
                        app = self.name
                    ))

            pindex      = osp.join(pnode, 'index.js')

            if not osp.exists(pindex) or force:
                with open(pindex, 'w') as f:
                    f.write(TEMPLATE_NODE_INDEX.format(
                        app = self.name
                    ))

            self.node = pnode

            # ensure the app has been linked.
            # link frappe to this app.
            app_ = self.get_frappe()
            app_.link(onto = self.name)

            log.info("Successfully hooked a Node App to {app}".format(app = self))
        else:
            log.warn("Cannot hook node to frappe. Already hooked.")

    def get_frappe(self):
        path = osp.abspath(osp.join(self.path, '..', 'frappe'))
        app_ = App(path)
        return app_

    def __repr__(self):
        return '<App {name}>'.format(name = self.name)

class Bench(object):
    def __init__(self, path = None):
        path      = assign_if_empty(path, os.getcwd())
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
        path  = osp.join(self.path, 'apps')
        apps_ = [ ]

        if not app:
            for app in os.listdir(path):
                papp = osp.join(path, app)
                app_ = App(papp)
                apps_.append(app_)
        else:
            apps  = sequencify(app)

            for app in apps:
                if self.has_app(app):
                    papp = osp.join(path, app)
                    app_ = App(papp)
                    apps_.append(app_)
                else:
                    log.info("App {app} not found.".format(app = app))
        
        return apps_

    def hook_app(self, app = None, node = True, raise_err = True, force = False):
        apps = sequencify(self.get_app(app, raise_err = raise_err))
        for app in apps:
            app.hook(node = node, force = force)

    def link_app(self, app = None, force = False, onto = None, raise_err = True):
        apps = sequencify(self.get_app(app, raise_err = raise_err))
        for app in apps:
            app.link(force = force, onto = onto)
            
            papp    = osp.join(self.path, 'app.js')
            content = None
            with open(papp, 'r') as f:
                content = f.read()

            with open(papp, 'a') as f:
                # Will break on Windows, but who the fuck cares?
                require = 'require("./apps/{app}/{app}/node");\n'.format(
                    app = app.name
                )
                if require.strip() not in content:
                    f.write(require)
        
    def __repr__(self):
        return '<Bench {name}>'.format(name = self.name)