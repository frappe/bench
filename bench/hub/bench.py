import os
import os.path as osp

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


        