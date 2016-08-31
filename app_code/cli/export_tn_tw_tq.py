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
import codecs
import glob
import json
import os
import re

# Import USFM-Tools
import datetime

from general_tools.file_utils import make_dir
from general_tools.print_utils import print_ok, print_error

base_dir = os.path.dirname(os.path.realpath(__file__))


root = '/var/www/vhosts/door43.org/httpdocs/data/gitrepo'
pages = os.path.join(root, 'pages')
api_v2 = '/var/www/vhosts/api.unfoldingword.org/httpdocs/ts/txt/2/'
kt_aliases = {}
tw_dict = {}

# Regexes for grabbing content
def_re = re.compile(r'===== (Definition|Facts|Description):? =====(.*?)\n[=(]', re.UNICODE | re.DOTALL)
kt_re = re.compile(r'====== (.*?) ======', re.UNICODE)
sub_re = re.compile(r'\n==== (.*) ====\n', re.UNICODE)
link_name_re = re.compile(r':([A-Za-z0-9\-]*)\]\]', re.UNICODE)
link_re = re.compile(r':([^:]*\|.*?)\]\]', re.UNICODE)
# noinspection SpellCheckingInspection
dw_link_re = re.compile(r'en:obe:[ktoher]*:(.*?)\]\]', re.UNICODE)
cf_re = re.compile(r'See also.*', re.UNICODE)
examples_re = re.compile(r'===== Examples from the Bible stories.*', re.UNICODE | re.DOTALL)
ex_txt_re = re.compile(r'\*\* (.*)', re.UNICODE)
fr_id_re = re.compile(r'[0-9][0-9][0-9]?/[0-9][0-9][0-9]?', re.UNICODE)
tN_re = re.compile(r'==== translationNotes.*', re.UNICODE | re.DOTALL)
it_re = re.compile(r'==== translationWords: ====(.*?)====', re.UNICODE | re.DOTALL)
tN_term_re = re.compile(r' \*\*(.*?)\*\*', re.UNICODE)
tN_text_re = re.compile(r' ?[–-] ?(.*)', re.UNICODE)
tN_text_re2 = re.compile(r'\* (.*)', re.UNICODE)
pub_re = re.compile(r'tag>.*publish.*', re.UNICODE)
suggest_re = re.compile(r'===== Translation Suggestions:? =====(.*?)[=(][TS]?', re.UNICODE | re.DOTALL)
q_re = re.compile(r'Q\?(.*)', re.UNICODE)
a_re = re.compile(r'A\.(.*)', re.UNICODE)
ref_re = re.compile(r'\[(.*?)]', re.UNICODE)

# Regexes for DW to HTML conversion
bold_re = re.compile(r'\*\*(.*?)\*\*', re.UNICODE)
li_re = re.compile(r' +\* ', re.UNICODE)
h3_re = re.compile(r'\n=== (.*?) ===\n', re.UNICODE)


def get_kt(f):
    with codecs.open(f, 'r', encoding='utf-8') as in_file:
        page = in_file.read()
    if not pub_re.search(page):
        return False

    # The filename is the ID
    kt = {'id': f.rsplit('/', 1)[1].replace('.txt', '')}
    kt_se = kt_re.search(page)
    if not kt_se:
        print('Term not found for {}'.format(kt['id']))
        return False
    kt['term'] = kt_se.group(1).strip()
    kt['sub'] = get_kt_sub(page)
    kt['def_title'], kt['def'] = get_kt_def(page)
    if not kt['def_title']:
        print('Definition or Facts not found for {}'.format(kt['id']))
        return False
    kt['cf'] = get_kt_cf(page)
    kt['def'] += get_kt_suggestions(page)
    return kt


def get_kt_def(page):
    def_se = def_re.search(page)
    if def_se:
        def_txt = def_se.group(2).rstrip()
        return def_se.group(1), get_html(def_txt)

    # if you are here, the kt def was not found
    return False, False


def get_kt_suggestions(page):
    sug_format = '<h2>Translation Suggestions</h2>{0}'
    sug_se = suggest_re.search(page)
    if not sug_se:
        return ''
    sug_txt = sug_format.format(sug_se.group(1).rstrip())
    return get_html(sug_txt)


def get_kt_sub(page):
    sub = ''
    sub_se = sub_re.search(page)
    if sub_se:
        sub = sub_se.group(1)
    return sub.strip()


def get_kt_cf(page):
    cf = []
    cf_se = cf_re.search(page)
    if cf_se:
        text = cf_se.group(0)
        cf = [x.group(1) for x in link_name_re.finditer(text)]
    return cf


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
    frame['id'] = fr_id_re.search(f).group(0).strip().replace('/', '-')

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
    tw_list = [x.split('|')[0] for x in link_re.findall(text)]
    tw_list += dw_link_re.findall(text)
    # Add to catalog
    entry = {'id': fr,
             'items': [{'id': x} for x in tw_list]
             }
    entry['items'].sort(key=lambda y: y['id'])
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
    for i in text.split('\n'):
        if not i.strip() or \
                'Comprehension Questions' in i or \
                '>>]]**' in i or \
                '<<]]**' in i or \
                '====' in i or \
                i.startswith(('{{tag>', '~~', '**[[', '\\\\')):
            continue

        item = {'ref': ''}
        tn_term_se = tN_term_re.search(i)
        if tn_term_se:
            item['ref'] = tn_term_se.group(1)
        tn_text_se = tN_text_re.search(i)
        if not tn_text_se:
            tn_text_se = tN_text_re2.search(i)
        try:
            item_text = tn_text_se.group(1).strip()
        except AttributeError:
            item_text = i
        item['text'] = get_html(item_text)
        tn.append(item)
    return tn


def run_kt(lang, date_today):
    kt_path = os.path.join(pages, lang, 'obe')
    key_terms = []
    for f in glob.glob('{0}/*/*.txt'.format(kt_path)):
        if 'home.txt' in f or '1-discussion-topic.txt' in f:
            continue
        kt = get_kt(f)
        if kt:
            key_terms.append(kt)
    for i in key_terms:  # type: dict
        if i['id'] in kt_aliases:
            i['aliases'] = [x for x in kt_aliases[i['id']] if x != i['term']]

    key_terms.sort(key=lambda y: len(y['term']), reverse=True)
    key_terms.append({'date_modified': date_today, 'version': '3'})
    api_path = os.path.join(api_v2, 'bible', lang)
    write_json('{0}/terms.json'.format(api_path), key_terms)


def run_tn(lang, date_today):
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
        frames.append({'date_modified': date_today, 'version': '3'})
        write_json('{0}/notes.json'.format(api_path), frames)
        if book not in tw_dict:
            print('Terms not found for {0}'.format(book))
            continue
        save_tw('{0}/tw_cat.json'.format(api_path), date_today, tw_dict[book])
        del tw_dict[book]


def save_tw(filepath, date_today, tw_book_dict):
    tw_cat = {'chapters': [], 'date_modified': date_today, 'version': '3'}
    for chp in tw_book_dict:
        tw_book_dict[chp].sort(key=lambda x: x['id'])
        entry = {'id': chp,
                 'frames': tw_book_dict[chp]
                 }
        tw_cat['chapters'].append(entry)
    tw_cat['chapters'].sort(key=lambda x: x['id'])
    write_json(filepath, tw_cat)


def run_cq(lang, date_today):
    cq_path = os.path.join(pages, lang, 'bible/questions/comprehension')
    for book in os.listdir(cq_path):
        book_questions = []  # type: list[dict]
        book_path = os.path.join(cq_path, book)
        if len(book) > 3:
            continue
        if not os.path.isdir(book_path):
            continue
        api_path = os.path.join(api_v2, book, lang)
        for f in glob.glob('{0}/*.txt'.format(book_path)):
            if 'home.txt' in f:
                continue
            book_questions.append(get_cq(f))
        # Check to see if there are published questions in this book
        pub_check = [x['cq'] for x in book_questions if len(x['cq']) > 0]
        if len(pub_check) == 0:
            print('No published questions for {0}'.format(book))
            continue
        book_questions.sort(key=lambda y: y['id'])
        book_questions.append({'date_modified': date_today})
        write_json('{0}/questions.json'.format(api_path), book_questions)


def get_cq(f):
    page = codecs.open(f, 'r', encoding='utf-8').read()
    chapter = {'id': f.rsplit('/')[-1].rstrip('.txt'), 'cq': []}
    if pub_re.search(page):
        chapter['cq'] = get_q_and_a(page)
    return chapter


def get_q_and_a(text):
    cq = []
    first_line = None
    for line in text.splitlines():
        line = line.strip()

        if not first_line and line.startswith('==='):
            first_line = line
            continue

        if line.startswith('\n') or \
                line == '' or \
                line.startswith('~~') or \
                line.startswith('===') or \
                line.startswith('{{') or \
                line.startswith('**[[') or \
                line.startswith('These questions will'):
            continue

        if q_re.search(line):
            item = {'q': q_re.search(line).group(1).strip()}
        elif a_re.search(line):
            item['a'] = a_re.search(line).group(1).strip()
            item['ref'] = fix_refs(ref_re.findall(item['a']))
            item['a'] = item['a'].split('[')[0].strip()
            cq.append(item)
            continue
        else:
            print_error('tQ error in {0}: {1}'.format(first_line, line))
    return cq


def fix_refs(refs):
    new_refs = []
    for i in refs:
        sep = '-'
        # noinspection PyBroadException
        try:
            chp, verses = i.split(':')

            if ',' in verses:
                sep = ','
            v_list = verses.split(sep)
            for v in v_list:
                new_refs.append('{0}-{1}'.format(chp.zfill(2), v.zfill(2)))
        except:
            print(i)

    return new_refs


if __name__ == '__main__':
    today = ''.join(str(datetime.date.today()).rsplit('-')[0:3])
    run_tn('en', today)
    # run_kt('en', today)
    # run_cq('en', today)
    print_ok('Finished: ', 'exported tN, tW, and tQ.')

