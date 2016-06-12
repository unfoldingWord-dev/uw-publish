#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#  Copyright (c) 2015, 2016 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Jesse Griffin <jesse@distantshores.org>
#  Phil Hopper <phillip_hopper@wycliffeassociates.org>


"""
This script publishes the Unlocked Bible into the tS v2 API.
"""

from __future__ import print_function, unicode_literals
from usfm_tools.transform import UsfmTransform
import os
import re
import sys
import codecs
import shutil
import argparse
import datetime
from general_tools.file_utils import write_file


class api_publish(object):

    source_dirs = [
        '/var/www/vhosts/api.unfoldingword.org/httpdocs/ulb/txt/1/',
        '/var/www/vhosts/api.unfoldingword.org/httpdocs/udb/txt/1/',
        '/var/www/vhosts/api.unfoldingword.org/httpdocs/pdb/txt/1/'
    ]

    api_v2 = '/var/www/vhosts/api.unfoldingword.org/httpdocs/ts/txt/2/'
    verse_re = re.compile(r'<verse number="([0-9]*)', re.UNICODE)

    def __init__(self, source):
        self.source = source

        # remember these so we can delete them
        self.temp_dir = ''

    def __enter__(self):
        return self

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb):
        # delete temp files
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @staticmethod
    def parse(usx):
        """
        Iterates through the source and splits it into frames based on the
        s5 markers.
        :param usx:
        """
        chunk_marker = '<note caller="u" style="s5"></note>'
        chapters = []
        chp = ''
        fr_id = 0
        chp_num = 0
        fr_list = []
        current_vs = -1
        for line in usx:
            if line.startswith('\n'):
                continue

            if "verse number" in line:
                current_vs = api_publish.verse_re.search(line).group(1)

            if 'chapter number' in line:
                if chp:
                    if fr_list:
                        fr_text = '\n'.join(fr_list)
                        try:
                            first_vs = api_publish.verse_re.search(fr_text).group(1)
                        except AttributeError:
                            print('myError, chp {0}'.format(chp_num))
                            print('Text: {0}'.format(fr_text))
                            sys.exit(1)
                        chp['frames'].append({'id': '{0}-{1}'.format(
                            str(chp_num).zfill(2), first_vs.zfill(2)),
                            'img': '',
                            'format': 'usx',
                            'text': fr_text,
                            'lastvs': current_vs
                        })
                    chapters.append(chp)
                chp_num += 1
                chp = {'number': str(chp_num).zfill(2),
                       'ref': '',
                       'title': '',
                       'frames': []
                       }
                fr_list = []
                continue

            if chunk_marker in line:
                if chp_num == 0:
                    continue

                # is there something else on the line with it? (probably an end-of-paragraph marker)
                if len(line.strip()) > len(chunk_marker):
                    # get the text following the chunk marker
                    rest_of_line = line.replace(chunk_marker, '')

                    # append the text to the previous line, removing the unnecessary \n
                    fr_list[-1] = fr_list[-1][:-1] + rest_of_line

                if fr_list:
                    fr_text = '\n'.join(fr_list)
                    try:
                        first_vs = api_publish.verse_re.search(fr_text).group(1)
                    except AttributeError:
                        print('Error, chp {0}'.format(chp_num))
                        print('Text: {0}'.format(fr_text))
                        sys.exit(1)

                    chp['frames'].append({'id': '{0}-{1}'.format(
                        str(chp_num).zfill(2), first_vs.zfill(2)),
                        'img': '',
                        'format': 'usx',
                        'text': fr_text,
                        'lastvs': current_vs
                    })
                    fr_list = []

                continue

            fr_list.append(line)

        # Append the last frame and the last chapter
        chp['frames'].append({'id': '{0}-{1}'.format(
            str(chp_num).zfill(2), str(fr_id).zfill(2)),
            'img': '',
            'format': 'usx',
            'text': '\n'.join(fr_list),
            'lastvs': current_vs
        })
        chapters.append(chp)
        return chapters

    @staticmethod
    def get_chunks(book):
        chunks = []
        for c in book:
            for frame in c['frames']:
                chunks.append({'id': frame['id'],
                               'firstvs': api_publish.verse_re.search(frame['text']).group(1),
                               'lastvs': frame["lastvs"]
                               })
        return chunks

    def run(self):

        today = ''.join(str(datetime.date.today()).rsplit('-')[0:3])
        dirs = []
        if self.source:
            dirs.append(self.source)
        else:
            for source_dir in api_publish.source_dirs:
                udb_dir = [os.path.join(source_dir, x) for x in os.listdir(source_dir)]
                dirs += udb_dir

        for d in dirs:
            ver, lang = d.rsplit('/', 1)[1].split('-', 1)
            self.temp_dir = '/tmp/{0}-{1}'.format(ver, lang)
            if os.path.isdir(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            UsfmTransform.buildUSX(d, self.temp_dir, '', True)
            print("#### Chunking...")
            for f in os.listdir(self.temp_dir):
                # use utf-8-sig to remove the byte order mark
                with codecs.open(os.path.join(self.temp_dir, f), 'r', encoding='utf-8-sig') as in_file:
                    usx = in_file.readlines()

                slug = f.split('.')[0].lower()
                print('     ({0})'.format(slug.upper()))
                book = self.parse(usx)
                payload = {'chapters': book,
                           'date_modified': today
                           }
                write_file(os.path.join(api_publish.api_v2, slug, lang, ver, 'source.json'), payload)
                chunks = self.get_chunks(book)
                write_file(os.path.join(api_publish.api_v2, slug, lang, ver, 'chunks.json'), chunks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-s', '--sourceDir', dest="sourcedir", default=False,
                        help="Source directory.")
    args = parser.parse_args(sys.argv[1:])

    with api_publish(args.sourcedir) as api:
        api.run()
    # chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/
