#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#  Copyright (c) 2014, 2016 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Jesse Griffin <jesse@distantshores.org>
#  Phil Hopper <phillip_hopper@wycliffeassociates.org>
#

from __future__ import print_function, unicode_literals
import argparse
import codecs
import glob
import json
import os
import re
import datetime
import sys
from general_tools.file_utils import make_dir
from general_tools.print_utils import print_ok, print_notice
from uw.update_catalog import update_catalog

root = '/var/www/vhosts/door43.org/httpdocs/data/gitrepo'
pages = os.path.join(root, 'pages')
api_v2 = '/var/www/vhosts/api.unfoldingword.org/httpdocs/ts/txt/2/'
kt_aliases = {}
tw_dict = {}

# Regexes for grabbing content
link_re = re.compile(r':([^:]*\|.*?)\]\]', re.UNICODE)
# noinspection SpellCheckingInspection
dw_link_re = re.compile(r'en:obe:[ktoher]*:(.*?)\]\]', re.UNICODE)
fr_id_re = re.compile(r'[0-9][0-9][0-9]?/[0-9][0-9][0-9]?', re.UNICODE)
tN_re = re.compile(r'==== translationNotes.*', re.UNICODE | re.DOTALL)
it_re = re.compile(r'==== translationWords: ====(.*?)====', re.UNICODE | re.DOTALL)
tN_term_re = re.compile(r' \*\*(.*?)\*\*', re.UNICODE)
tN_text_re = re.compile(r' ?[–-] ?(.*)', re.UNICODE)
tN_text_re2 = re.compile(r'\* (.*)', re.UNICODE)
pub_re = re.compile(r'tag>.*publish.*', re.UNICODE)

# Regexes for DW to HTML conversion
bold_re = re.compile(r'\*\*(.*?)\*\*', re.UNICODE)
li_re = re.compile(r' +\* ', re.UNICODE)
h3_re = re.compile(r'\n=== (.*?) ===\n', re.UNICODE)


def get_html(text):
    # add ul/li
    text = bold_re.sub(r'<b>\1</b>', text)
    text = h3_re.sub(r'<h3>\1</h3>', text)
    text = get_html_list(text)
    return text.strip()


def get_html_list(text):
    started = False
    new_text = []
    for line in text.split('\n'):
        if li_re.search(line):
            if not started:
                started = True
                new_text.append('<ul>')
            line = li_re.sub('<li>', line)
            new_text.append('{0}</li>'.format(line))
        else:
            if started:
                started = False
                new_text.append('</ul>')
            new_text.append(line)
    if started:
        new_text.append('</ul>')
    return ''.join(new_text)


def write_json(outfile, p):
    """
    Simple wrapper to write a file as JSON.
    """
    make_dir(outfile.rsplit('/', 1)[0])
    f = codecs.open(outfile, 'w', encoding='utf-8')
    f.write(get_dump(p))
    f.close()


def get_dump(j):
    return json.dumps(j, sort_keys=True)


def get_frame(f, book):
    page = codecs.open(f, 'r', encoding='utf-8').read()
    if not pub_re.search(page):
        return False
    frame = {}
    get_aliases(page, f)
    frame_id = fr_id_re.search(f).group(0)  # type: unicode
    frame['id'] = frame_id.strip().replace('/', '-')

    tn = get_tn(page)
    if not tn and not f.endswith(('/00.txt', '/000.txt')):
        print('Notes not found for ' + f)

    frame['tn'] = tn
    get_tw_list(frame['id'], page, book)
    return frame


def get_tw_list(fr_id, page, book):
    # Get book, chapter and id, create chp in tw_dict if it doesn't exist
    chp, fr = fr_id.split('-')
    if book not in tw_dict:
        tw_dict[book] = {}
    if chp not in tw_dict[book]:
        tw_dict[book][chp] = []
    # Get list of tW from page
    it_se = it_re.search(page)
    if not it_se:
        # we already displayed a message for this in get_aliases
        return

    text = it_se.group(1).strip()
    # tw_list = [x.split('|')[0] for x in link_re.findall(text)]
    # tw_list += dw_link_re.findall(text)
    tw_list = [x.split('|')[0] for x in dw_link_re.findall(text)]
    # Add to catalog
    entry = {'id': fr,
             'items': [{'id': x} for x in tw_list]
             }
    # entry['items'].sort(key=lambda y: y['id'])
    tw_dict[book][chp].append(entry)


def get_aliases(page, f):
    it_se = it_re.search(page)
    if not it_se:
        if not f.endswith(('/00.txt', '/000.txt')):
            print('Terms not found for {0}'.format(f))

        return

    text = it_se.group(1).strip()
    its = link_re.findall(text)
    for t in its:
        term, alias = t.split('|')
        if term not in kt_aliases:
            kt_aliases[term] = []
        kt_aliases[term].append(alias)


def get_tn(page):
    tn = []
    tn_se = tN_re.search(page)
    if not tn_se:
        return tn

    text = tn_se.group(0)
    lines = text.split('\n')
    found_first = False
    for i in range(0, len(lines)):
        line = lines[i]

        if line.startswith('===='):
            if found_first:
                break
            found_first = True

        if not line.strip() or \
                'Comprehension Questions' in line or \
                '>>]]**' in line or \
                '<<]]**' in line or \
                '====' in line or \
                line.startswith(('{{tag>', '~~', '**[[', '\\\\')):
            continue

        item = {'ref': ''}
        tn_term_se = tN_term_re.search(line)
        if tn_term_se:
            item['ref'] = tn_term_se.group(1)
        tn_text_se = tN_text_re.search(line)
        if not tn_text_se:
            tn_text_se = tN_text_re2.search(line)
        try:
            item_text = tn_text_se.group(1).strip()
        except AttributeError:
            item_text = line
        item['text'] = get_html(item_text)
        tn.append(item)
    return tn


def run_tn(version, lang, date_today):
    """
    Exports tN from Dokuwiki
    :param int version:
    :param str|unicode lang:
    :param str|unicode date_today:
    :return: None
    """
    tn_path = os.path.join(pages, lang, 'bible/notes')
    for book in os.listdir(tn_path):
        book_path = os.path.join(tn_path, book)
        if len(book) > 3:
            continue
        if not os.path.isdir(book_path):
            continue
        api_path = os.path.join(api_v2, book, lang)
        if not os.path.isdir(api_path):
            continue
        frames = []
        for chapter in os.listdir(book_path):
            try:
                int(chapter)
            except ValueError:
                continue
            for f in glob.glob('{0}/{1}/*.txt'.format(book_path, chapter)):
                if 'home.txt' in f:
                    continue
                if '00/intro.txt' in f:
                    continue
                frame = get_frame(f, book)
                if frame:
                    frames.append(frame)

        frames.sort(key=lambda x: x['id'])
        frames.append({'date_modified': date_today, 'version': str(version)})
        write_json('{0}/notes.json'.format(api_path), frames)
        if book not in tw_dict:
            print('Terms not found for {0}'.format(book))
            continue
        save_tw(version, '{0}/tw_cat.json'.format(api_path), date_today, tw_dict[book])
        del tw_dict[book]

    print()
    print('Updating the catalogs...', end=' ')
    update_catalog()
    print('finished.')


def save_tw(version, filepath, date_today, tw_book_dict):
    tw_cat = {'chapters': [], 'date_modified': date_today, 'version': str(version)}
    for chp in tw_book_dict:
        tw_book_dict[chp].sort(key=lambda x: x['id'])
        entry = {'id': chp,
                 'frames': tw_book_dict[chp]
                 }
        tw_cat['chapters'].append(entry)
    tw_cat['chapters'].sort(key=lambda x: x['id'])
    write_json(filepath, tw_cat)


if __name__ == '__main__':
    print()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--version', dest='version', default=False,
                        required=True, help='The version number.')

    args = parser.parse_args(sys.argv[1:])

    today = ''.join(str(datetime.date.today()).rsplit('-')[0:3])

    print_ok('STARTING: ', 'publishing tN from Dokuwiki.')
    run_tn(args.version, 'en', today)
    print_ok('ALL FINISHED: ', 'publishing tN from Dokuwiki.')
    print_notice('Don\'t forget to notify the interested parties.')
