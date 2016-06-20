#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#    This file gets chunk information from the api.
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
from general_tools.url_utils import get_url

if __name__ == '__main__':
    notes_dir = '/var/www/vhosts/door43.org/httpdocs/data/gitrepo/pages/en/bible/notes'
    api_url = 'https://api.unfoldingword.org/bible/txt/1/{0}/chunks.json'
    dirs = os.walk(notes_dir).next()[1]

    # loop through the books
    for d in dirs:
        print(d)
        old_chunks = json.loads(get_url(api_url.format(d)))
        chunks = []

        for old_chunk in old_chunks:
            chap_num = int(old_chunk['chp'])
            found = [x for x in chunks if x['chapter'] == chap_num]
            if found:
                chunk = found[0]
            else:
                chunk = {'chapter': chap_num, 'first_verses': []}
                chunks.append(chunk)

            chunk['first_verses'].append(int(old_chunk['firstvs']))

        s = json.dumps(chunks, indent=2, sort_keys=True, separators=(',', ': '))
        s = s.replace('[\n      ', '[')
        s = s.replace(',\n      ', ', ')
        s = s.replace('\n    ]', ']')
        file_name = '/home/team43/chunks/' + d + '.json'
        write_file(file_name, s)

    print('Finished')
