from __future__ import absolute_import

from collections import Mapping
import logging

import elasticsearch as es

log = logging.getLogger(__name__)
log.setLevel(logging.NOTSET)

def doctype_to_index(name):
    name = name.lower()
    name = name.replace(' ', '')

    return name

class ESearch(object):
    """
    Helper for ElasticSearch
    """
    def __init__(self,
        host = 'localhost', # TODO: multiple hosts :)
        port = 9200
    ):
        self.client = es.Elasticsearch()
    
    def insert(self, index, data, create = True, exists_ok = True, refresh = True):
        """
        :param: refresh - Make data available immediately for search.
        """
        es     = self.client
        
        index  = doctype_to_index(index)
        ignore = [400] if exists_ok else None

        if not es.indices.exists(index) or create:
            log.debug('Creating Index {index}'.format(index = index))
            res = es.indices.create(index = index, ignore = ignore)
            log.debug('Response: {response}'.format(response = res))
        else:
            raise ValueError('Index {index} does not exist.'.format(index = index))
        
        if isinstance(data, Mapping): # if, only a single value is given for insert.
            data = [data]
            
        bulk = [ ]
        for d in data:
            # action / metadata
            bulk.append({
                "index": {
                    "_index": index,
                     "_type": "_doc",
                       "_id": d['name']
                }
            })
            
            # data
            del d['name']
            bulk.append(d)

        es.bulk(index = index, body = bulk, refresh = refresh, ignore = ignore)