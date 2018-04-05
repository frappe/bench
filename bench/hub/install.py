from __future__ import absolute_import

import logging
import click

from bench.hub.util import popen, which

log = logging.getLogger(__name__)

def brew_install(formulae, caskroom = False, update = False, upgrade = False, verbose = True):
    brew = which('brew')
    if not brew:
        log.info('Installing HomeBrew')
        popen('{ruby} -e "$({curl} -sL https://git.io/get-brew)"'.format(
            curl = which('curl', raise_err = True),
            ruby = which('ruby', raise_err = True)
        ))
        
    brew = which('brew', raise_err = True)

    if update:
        popen('{brew} update'.format(brew = brew))

    formulae = [formulae] if isinstance(formulae, str) else formulae

    if caskroom:
        popen('{brew} tap caskroom/{caskroom}'.format(
            brew     = brew,
            caskroom = caskroom
        ))

    for formula in formulae:
        ret = popen('{brew} {cask} install {formula}'.format(
            brew    = brew,
            cask    = 'cask' if caskroom else '',
            formula = formula
        ), output   = verbose)

        # TODO: caskroom upgrade
        
        if ret and upgrade:
            popen('{brew} upgrade {formula}'.format(
                brew    = brew,
                formula = formula
            ), output   = verbose)