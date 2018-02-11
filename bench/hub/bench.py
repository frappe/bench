from __future__ import absolute_import

import os
import os.path as osp
import json

from bench.hub.util import popen

def check_bench(path, raise_err = False):
    """
    """
    # I know, bad check.
    path = osp.join(path, 'apps', 'frappe')
    
    if not osp.exists(path) and not osp.exists(osp.join(path, 'sites')):
        if raise_err:
            raise TypeError('{path} not a Bench Instance.'.format(
                path = path
            ))
        else:
            return False
    return True
class Bench(object):

    def __init__(self, path):
        check_bench(path, raise_err = True)

        self.path = path
        self.name = osp.basename(path)

    def get_config(self):
        path = osp.join(self.path, 'sites', 'common_site_config.json')

        with open(path, 'r') as f:
            config = json.load(f)
        
        return config

    def has_app(self, app, installed = False):
        path = osp.join(self.path, 'apps', app)
        if osp.exists(path):
            if installed:
                pip = osp.join(self.path, 'env', 'bin', 'pip')
                ret = popen('{pip} show {app}'.format(
                    pip = pip, app = app
                ), output = False)
                
                if ret:
                    return True
                else:
                    return False
                    
            return True

        return False

    def get_sites(self):
        sites = list()

        path  = osp.join(self.path, 'sites')
        for site in os.listdir(path):
            abspath  = osp.join(path, site)
            if check_site(abspath, raise_err = False):
                site = Site(abspath)

                sites.append(site)

        return sites

    def __repr__(self):
        return '<Bench {name}>'.format(name = self.name)

def check_site(path, raise_err = True):
    if not osp.exists(osp.join(path, 'site_config.json')):
        if raise_err:
            raise TypeError('{path} not a Site.'.format(
                path = path
            ))
        else:
            return False
    return True
class Site(object):
    def __init__(self, path):
        check_site(path, raise_err = True)

        self.path = path
        self.name = osp.basename(path)

    def __repr__(self):
        return '<Site {name}>'.format(name = self.name)