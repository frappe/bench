from __future__ import absolute_import

import os
import os.path as osp

from bench.hub.util import assign_if_empty, makedirs, which

def setup_config(location = None):
    location = assign_if_empty(location, osp.expanduser('~'))
    path     = osp.join(location, '.hub')
    makedirs(path, exists_ok = True)

    return path

def setup_procfile(reinit = False):
    path     = setup_config()
    procfile = osp.join(path, 'Procfile')

    content  = \
"""
search: {elasticsearch}
""".format(elasticsearch = which('elasticsearch'))

    if not osp.exists(procfile) or reinit:
        with open(procfile, 'w') as f:
            f.write(content)

    return procfile