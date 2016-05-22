#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#  Copyright (c) 2016 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Phil Hopper <phillip_hopper@wycliffeassociates.org>
#

from __future__ import print_function, unicode_literals
from general_tools.print_utils import print_notice
from uw.update_catalog import update_catalog

if __name__ == '__main__':
    print()
    print_notice('Updating the catalogs...')
    update_catalog()
    print_notice('Finished updating the catalogs.')
