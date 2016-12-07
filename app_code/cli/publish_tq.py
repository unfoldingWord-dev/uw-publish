from __future__ import print_function, unicode_literals
import argparse
import codecs
import os
import re
import sys
import datetime
import shutil
import tempfile
from general_tools.file_utils import write_file, unzip
from general_tools.print_utils import print_error, print_ok, print_notice
from general_tools.url_utils import join_url_parts, download_file
from uw.update_catalog import update_catalog

api_v2 = '/var/www/vhosts/api.unfoldingword.org/httpdocs/ts/txt/2/'

q_re = re.compile(r'Q\?(.*)', re.UNICODE)
a_re = re.compile(r'A\.(.*)', re.UNICODE)
ref_re = re.compile(r'\[(.*?)]', re.UNICODE)

# remember these so we can delete them
download_dir = ''


def main(date_today, tag, version):
    global download_dir

    repo = 'https://git.door43.org/Door43/en-tq'
    download_dir = tempfile.mkdtemp(prefix='tempTQ_')
    download_url = join_url_parts(repo, 'archive', '{0}.zip'.format(tag))
    downloaded_file = os.path.join(download_dir, 'tQ.zip')

    # download the repository
    try:
        print('Downloading {0}...'.format(download_url), end=' ')
        download_file(download_url, downloaded_file)
    finally:
        print('finished.')

    try:
        print('Unzipping...'.format(downloaded_file), end=' ')
        unzip(downloaded_file, download_dir)
    finally:
        print('finished.')

    # examine the repository
    source_root = os.path.join(download_dir, 'en-tq', 'content')
    books = [x for x in os.listdir(source_root) if os.path.isdir(os.path.join(source_root, x))]

    for book in books:
        print('Processing {}.'.format(book))
        book_dir = os.path.join(source_root, book)
        api_path = os.path.join(api_v2, book, 'en')
        # noinspection PyUnresolvedReferences
        book_questions = []  # type: list[dict]

        for entry in os.listdir(book_dir):
            file_name = os.path.join(book_dir, entry)

            # we are only processing files
            if not os.path.isfile(file_name):
                continue

            # we are only processing markdown files
            if entry[-3:] != '.md':
                continue

            book_questions.append(get_cq(file_name))

        # Check to see if there are published questions in this book
        pub_check = [x['cq'] for x in book_questions if len(x['cq']) > 0]
        if len(pub_check) == 0:
            print('No published questions for {0}'.format(book))
            continue
        book_questions.sort(key=lambda y: y['id'])
        book_questions.append({'date_modified': date_today, 'version': version})
        write_file('{0}/questions.json'.format(api_path), book_questions, indent=2)

    print()
    print('Updating the catalogs...', end=' ')
    update_catalog()
    print('finished.')


def get_cq(f):
    page = codecs.open(f, 'r', encoding='utf-8').read()
    return {'id': f.rsplit('/')[-1].rstrip('.md'), 'cq': get_q_and_a(page)}


def get_q_and_a(text):
    cq = []
    first_line = None
    for line in text.splitlines():
        line = line.strip()

        if not first_line and line.startswith('#'):
            first_line = line
            continue

        if line.startswith('\n') or \
                line == '' or \
                line.startswith('~~') or \
                line.startswith('#') or \
                line.startswith('{{') or \
                line.startswith('__[') or \
                line.startswith('These questions will'):
            continue

        if q_re.search(line):
            item = {'q': q_re.search(line).group(1).strip()}
        elif a_re.search(line):
            item['a'] = a_re.search(line).group(1).strip()
            item['ref'] = fix_refs(ref_re.findall(item['a']))
            item['a'] = item['a'].split(str('['))[0].strip()
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
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--version', dest='version', default=False,
                        required=True, help='The version number of this resource.')
    parser.add_argument('-t', '--tag', dest='tag', default='master',
                        required=False, help='Branch or tag to use as the source. Default is master.')

    args = parser.parse_args(sys.argv[1:])
    today = ''.join(str(datetime.date.today()).rsplit(str('-'))[0:3])

    try:
        print_ok('STARTING: ', 'publishing tQ repository.')
        main(today, args.tag, args.version)
        print_ok('ALL FINISHED: ', 'publishing tQ repository.')
        print_notice('Don\'t forget to notify the interested parties.')

    finally:
        # delete temp files
        if os.path.isdir(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
