import os
import os.path as osp
import json

import subprocess

def check_bench(path, raise_err = False):
    """
    """
    # I know, bad check.
    path = osp.join(path, 'apps', 'frappe')
    if not osp.exists(path):
        if raise_err:
            raise TypeError('{path} Not a Bench Instance.'.format(
                path = path
            ))
        else:
            return False
    return True

class Bench(object):
    def __init__(self, path):
        check_bench(path, raise_err = True)

        self.path = path

    def get_config(self):
        path = osp.join(self.path, 'sites', 'common_site_config.json')

        with open(path, 'r') as f:
            config = json.load(f)
        
        return config

    def has_app(self, app, installed = False):
        path = osp.join(self.path, 'apps', app)
        if osp.exists(path):
            if installed:
                pip  = osp.join(self.path, 'env', 'bin', 'pip')
                out  = subprocess.check_output('{pip} show {app}'.format(
                    pip = pip, app = app
                ), shell = True)
                
                if out:
                    return True
                else:
                    return False
                    
            return True

        return False

    def __repr__(self):
        return '<Bench {path}>'.format(path = self.path)

        