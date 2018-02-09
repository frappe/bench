from __future__ import absolute_import

import os
import os.path as osp

from bench.hub.config import set_config
from bench.hub.bench  import Bench, check_bench
from bench.hub.util   import assign_if_empty, which
from bench.hub.setup  import setup_procfile

def init(bench = None, group = None, validate = False):
    benches = [Bench(path) for path in bench if check_bench(path, raise_err = validate)]
    group   = assign_if_empty(group, os.getcwd())

    for path in os.listdir(group):
        if check_bench(path, raise_err = validate):
            bench = Bench(path)
            benches.append(bench)

    if not benches:
        raise ValueError('No benches found at {path}'.format(path = group))

    for bench in benches:
        if not bench.has_app('erpnext', installed = True) and validate:
            raise ValueError('{bench} does not have erpnext for hub installed.'.format(
                bench = bench
            ))

    setup_procfile()

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