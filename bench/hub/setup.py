from __future__ import absolute_import

import os
import os.path as osp

from   bench.hub.bench  import Bench
from   bench.hub.util   import assign_if_empty, makedirs, which
import bench

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

def search():
    path    = setup_config()
    pmap    = osp.join(path, 'map')
    makedirs(pmap, exists_ok = True)
    
    benches = [(conf['id'], Bench(conf['path'])) for conf in bench.hub.config.get_config('benches')]
    for i, b in benches:
        sites = b.get_sites()
        bconf = osp.join(pmap, i)

        if sites:
            makedirs(bconf, exists_ok = True)

        for site in sites:
            sconf = site.get_config()
            psite = osp.join(bconf, site.name)
            makedirs(psite, exists_ok = True)