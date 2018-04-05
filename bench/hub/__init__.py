from __future__ import absolute_import

import os
import os.path as osp
import json

from collections import MutableMapping

from bench.hub.config   import Config, get_config, set_config
from bench.hub.bench    import Bench, check_bench
from bench.hub.util     import assign_if_empty, which, get_uuid
from bench.hub.setup    import setup_procfile

from bench.hub.database      import DataBase
from bench.hub.elasticsearch import ESearch

def init(bench = None, group = None, validate = False, reinit = False):
    benches = [Bench(path) for path in bench if check_bench(path, raise_err = validate)]
    group   = assign_if_empty(group, os.getcwd())

    for path in os.listdir(group):
        abspath = osp.join(group, path)
        if check_bench(abspath, raise_err = validate):
            bench = Bench(abspath)
            benches.append(bench)
            
    if not benches:
        print('No benches found at {path}'.format(path = group))
        return

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
    set_config('environment', 'development')

    setup_procfile(reinit = reinit)

def migrate(doctype = [ ], file_ = None):
    doctypes = [dict(name = doc, fields = None) for doc in doctype]

    # Load from file.
    if file_:
        path = osp.abspath(file_)
        if not osp.exists(path):
            raise ValueError('{file} does not exist.'.format(file = file))

        with open(path, 'r') as f:
            temp = json.load(f)
            
        if isinstance(temp['doctype'], MutableMapping):
            temp['doctype'] = [temp['doctype']]

        doctypes = doctypes + temp['doctype']

    elasitc = ESearch()
    
    benches = [Bench(conf['path']) for conf in get_config('benches')]
    for b in benches:
        sites = b.get_sites()
        for site in sites:
            sconf  = site.get_config()
            
            dbname = sconf.get('db_name')
            db     = DataBase(dbname,
                host     = sconf.get('db_host', 'localhost'),
                port     = sconf.get('db_port', 3306),
                user     = sconf.get('db_user', dbname), # WTF Frappe?
                password = sconf.get('db_password'),
                charset  = sconf.get('db_charset', 'utf8')
            )
            db.connect()

            for doc in doctypes:
                fields  = doc['fields'] if 'fields' in doc else [ ]
                results = db.sql("SELECT {fields} FROM `tab{doctype}`".format(
                    doctype = doc['name'],
                    fields  = ", ".join(['name'] + fields) if fields else '*',
                ))

                elasitc.insert(doc['name'], results)

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