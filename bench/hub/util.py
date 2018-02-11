import os
import os.path as osp
import errno

import subprocess

from distutils.spawn import find_executable

def makedirs(dirs, exists_ok = False):
    try:
        os.makedirs(dirs)
    except OSError as e:
        if not exists_ok or e.errno != errno.EEXIST:
            raise

def assign_if_empty(a, b):
    if not a:
        a = b
    return a

def which(executable, raise_err = False):
    exec_ = find_executable(executable)
    if not exec_ and raise_err:
        raise ValueError('{executable} executable not found'.format(
            executable = executable
        ))
    return exec_

def popen(command, *args, **kwargs):
    output    = kwargs.get('output')
    raise_err = kwargs.get('raise_err')

    proc    = subprocess.Popen(command,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        shell  = True
    )

    if output:
        for line in proc.stdout.readlines():
            print(line)
            
    proc.stdout.close()

    return_ = proc.wait()

    if raise_err:
        raise subprocess.CalledProcessError(return_, command)

    return return_