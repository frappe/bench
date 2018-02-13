from __future__ import absolute_import

import os
import os.path as osp

from   bench.hub.bench  import Bench
from   bench.hub.util   import assign_if_empty, makedirs, which
import bench

LOGSTASH_CONFIGURATION = \
"""
input {{
    jdbc {{
        jdbc_connection_string   => "jdbc:{db_dialect}://{db_host}:{db_port}/{db_name}"
        jdbc_user                => "{db_user}"
        jdbc_password            => "{db_pass}"
        jdbc_driver_library      => "{driver_path}"
        jdbc_driver_class        => "{driver_class}"
        jdbc_validate_connection => true
        statement                => "{statement}"
    }}
}}

output {{
    elasticsearch {{
        index         => "{es_index}"
        document_type => "{es_doctype}"
        document_id   => "{es_id}"
    }}
}}
"""

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

def search(jar = None):
    if not jar:
        raise ValueError('No jar file found.')

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
            sconf  = site.get_config()
            psite  = osp.join(bconf, site.name)
            makedirs(psite, exists_ok = True)

            dbname = sconf.get('db_name')
            config = LOGSTASH_CONFIGURATION.format(
                db_dialect   = 'mariadb',
                driver_path  = jar,
                driver_class = 'Java::org.mariadb.jdbc.Driver',

                db_name      = dbname,
                db_host      = sconf.get('db_host', 'localhost'),
                db_port      = sconf.get('db_port', 3306),
                
                db_user      = sconf.get('db_user', dbname),
                db_pass      = sconf.get('db_password', '')
            )