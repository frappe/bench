import os
import os.path as osp
import errno

def makedirs(dirs, exists_ok = False):
    try:
        os.makedirs(dirs)
    except OSError as e:
        if not exists_ok or e.errno != errno.EEXIST:
            raise