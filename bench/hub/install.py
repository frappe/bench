from __future__ import absolute_import

import logging
import click

from bench.hub.util import popen, which

log = logging.getLogger(__name__)

def brew_install(formulae, upgrade = False, verbose = True):
    brew = which('brew')
    if not brew:
        log.info('Installing HomeBrew')
        popen('{ruby} -e "$({curl} -sL https://git.io/get-brew)"'.format(
            curl = which('curl', raise_err = True),
            ruby = which('ruby', raise_err = True)
        ))
        
    brew     = which('brew', raise_err = True)
    formulae = [formulae] if isinstance(formulae, str) else formulae
    
    for formula in formulae:
        ret = popen('{brew} install {formula}'.format(
            brew    = brew,
            formula = formula
        ), output   = verbose)

        if ret and upgrade:
            popen('{brew} upgrade {formula}'.format(
                brew    = brew,
                formula = formula
            ), output   = verbose)