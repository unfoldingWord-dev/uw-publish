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

"""
This module will check a translated json OBS file and produce a cleaned version in the same directory
"""

from __future__ import print_function, unicode_literals
import argparse
import codecs
import json
import sys
from app_code.obs.obs_classes import OBS


def clean_obs_json_file(json_file):

    obs_obj = OBS(json_file)

    # check data integrity
    if not obs_obj.verify_all():
        sys.exit(1)

    # write the cleaned file
    cleaned_name = json_file.replace('.json', '')
    cleaned_name += '.cleaned.json'
    with codecs.open(cleaned_name, 'w', 'utf-8-sig') as out_file:
        json.dump(obs_obj.__dict__, out_file, sort_keys=True, indent=2)

    print('Finished. {0}'.format(cleaned_name))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-f', '--file', dest='input_file', default=False,
                        required=True, help='The json file to check and clean.')

    args = parser.parse_args(sys.argv[1:])

    clean_obs_json_file(args.input_file)
