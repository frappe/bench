from __future__ import absolute_import

import os.path as osp
import json

from bench.hub.setup  import setup_config
from bench.hub.util   import makedirs

class Config(dict):
    def __init__(self, *args, **kwargs):
        self.super = super(Config, self)
        self.update(*args, **kwargs)

    def __setitem__(self, keys, value):
        keys   = keys.split('.')
        keys.reverse()

        config = Config()

        for i, k in enumerate(keys):
            if i == 0:
                config  = Config(**{ k: value })
            else:
                config  = Config(**{ k: config })

        self.super.update(config)
    
def set_config(key, value):
    path   = setup_config()

    pconf  = osp.join(path, 'config.json')
    config = Config()

    if not osp.exists(pconf):
        with open(pconf, 'w') as f:
            json.dump(config, f)

    with open(pconf, 'r') as f:
        config  = Config(json.load(f))
        
    config[key] = value

    with open(pconf, 'w') as f:
        json.dump(config, f)