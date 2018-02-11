from __future__ import absolute_import

import os
import os.path as osp

from bench.hub.config import Config, get_config, set_config
from bench.hub.bench  import Bench, check_bench
from bench.hub.util   import assign_if_empty, which, get_uuid
from bench.hub.setup  import setup_procfile

def init(bench = None, group = None, validate = False, reinit = False):
    benches = [Bench(path) for path in bench if check_bench(path, raise_err = validate)]
    group   = assign_if_empty(group, os.getcwd())

    for path in os.listdir(group):
        abspath = osp.join(group, path)
        if check_bench(abspath, raise_err = validate):
            bench = Bench(abspath)
            benches.append(bench)
            
    if not benches:
        raise ValueError('No benches found at {path}'.format(path = group))

    confs = list()
    for bench in benches:
        if not bench.has_app('erpnext', installed = True) and validate:
            raise ValueError('{bench} does not have erpnext for hub installed.'.format(
                bench = bench
            ))
        else:
            # TODO: Check if site has Hub enabled.
            confs.append({
                  'id': get_uuid(),
                'path': bench.path
            })
            
    set_config('benches', confs)

    setup_procfile(reinit = reinit)

def migrate():
    benches = [Bench(conf['path']) for conf in get_config('benches')]

def start(daemonize = False):
    if daemonize:
        pass
    else:
        procfile = setup_procfile()
        honcho   = which('honcho')

        args     = [honcho, 'start',
            '-f', procfile
        ]

        os.execv(honcho, args)