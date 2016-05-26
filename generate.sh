#!/usr/bin/env bash
# -*- coding: utf8 -*-
#
#  Copyright (c) 2016 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Phil Hopper <phillip_hopper@wycliffeassociates.org>
#
#  Usage: ./generate.sh

## install/update git submodules
#git submodule sync
#git submodule update --init
#git pull --recurse-submodules

# install/update python libraries
pip install -r requirements.txt
