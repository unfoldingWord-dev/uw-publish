#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#    This file gets chunk information from the door43 notes directory.
#
#    Copyright (c) 2016 unfoldingWord
#    http://creativecommons.org/licenses/MIT/
#    See LICENSE file for details.
#
#    Contributors:
#    Phil Hopper <phillip_hopper@wycliffeassociates.org>

from __future__ import print_function, unicode_literals
from general_tools.file_utils import write_file
import json
import os


if __name__ == '__main__':
    notes_dir = '/var/www/vhosts/door43.org/httpdocs/data/gitrepo/pages/en/bible/notes'
    dirs = os.walk(notes_dir).next()[1]

    # loop through the books
    for d in dirs:
        full_dir = os.path.join(notes_dir, d)
        chunks = []

        for chap in range(1, 151):
            print(d)
            if d == 'psa':
                chap_dir = os.path.join(full_dir, str(chap).zfill(3))
            else:
                chap_dir = os.path.join(full_dir, str(chap).zfill(2))

            if not os.path.isdir(chap_dir):
                continue

            chap_obj = {'chapter': chap, 'first_verses': []}

            # loop through the files
            # files = os.walk(chap_dir).next()[2]
            for chunk in range(1, 180):
                if d == 'psa':
                    chunk_file = os.path.join(chap_dir, str(chunk).zfill(3)) + '.txt'
                else:
                    chunk_file = os.path.join(chap_dir, str(chunk).zfill(2)) + '.txt'

                if not os.path.isfile(chunk_file):
                    continue

                chap_obj['first_verses'].append(chunk)

            chunks.append(chap_obj)

        # write the chunks file
        s = json.dumps(chunks, indent=2, sort_keys=True, separators=(',', ': '))
        s = s.replace('[\n      ', '[')
        s = s.replace(',\n      ', ', ')
        s = s.replace('\n    ]', ']')
        file_name = '/home/team43/chunks/' + d + '.json'
        write_file(file_name, s)

    print('Finished')
