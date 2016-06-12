#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#    This file imports text that has been merged into valid USFM format, one file per book.
#
#    Copyright (c) 2016 unfoldingWord
#    http://creativecommons.org/licenses/MIT/
#    See LICENSE file for details.
#
#    Contributors:
#    Phil Hopper <phillip_hopper@wycliffeassociates.org>

from __future__ import print_function, unicode_literals
import argparse
import codecs
import json
import os
import re
import shutil
import sys
import datetime
from glob import glob
from general_tools.print_utils import print_error, print_ok, print_notice
from uw.update_catalog import update_catalog
from app_code.bible.bible_classes import BibleMetaData
from app_code.bible.content import Book, Chapter, Chunk
from general_tools.file_utils import unzip, make_dir, write_file
from general_tools.url_utils import download_file, get_url, join_url_parts
from app_code.cli.api_publish import api_publish

if sys.version_info < (3, 0):
    prompt = raw_input
else:
    prompt = input

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2


# remember these so we can delete them
download_dir = ''

chunk_url = 'https://api.unfoldingword.org/ts/txt/2/{0}/en/ulb/chunks.json'
out_template = '/var/www/vhosts/api.unfoldingword.org/httpdocs/{0}/txt/1/{1}-{2}'

id_re = re.compile(r'\\id\s+(\w{3}).*')
s5_re = re.compile(r'\\s5\s*')
nl_re = re.compile(r'\n{2,}')

# TODO: change these to point to the API when it is available
vrs_file = 'https://raw.githubusercontent.com/unfoldingWord-dev/uw-api/develop/static/versification/ufw/ufw.vrs'
book_file = 'https://raw.githubusercontent.com/unfoldingWord-dev/uw-api/develop/static/versification/ufw/books-en.json'


def main(git_repo, domain):

    global download_dir, out_template

    # clean up the git repo url
    if git_repo[-4:] == '.git':
        git_repo = git_repo[:-4]

    if git_repo[-1:] == '/':
        git_repo = git_repo[:-1]

    # get the versification data
    vrs = get_versification()  # type: list<Book>

    # initialize some variables
    today = ''.join(str(datetime.date.today()).rsplit('-')[0:3])
    download_dir = '/tmp/{0}'.format(git_repo.rpartition('/')[2])
    make_dir(download_dir)
    downloaded_file = '{0}/{1}.zip'.format(download_dir, git_repo.rpartition('/')[2])
    file_to_download = join_url_parts(git_repo, 'archive/master.zip')
    books_published = {}
    metadata_obj = None
    usfm_dir = None

    # download the repository
    try:
        print('Downloading {0}...'.format(file_to_download), end=' ')
        if not os.path.isfile(downloaded_file):
            download_file(file_to_download, downloaded_file)
    finally:
        print('finished.')

    try:
        print('Unzipping...'.format(downloaded_file), end=' ')
        unzip(downloaded_file, download_dir)
    finally:
        print('finished.')

    # examine the repository
    for root, dirs, files in os.walk(download_dir):

        if 'meta.json' in files:
            # read the metadata
            try:
                print('Reading the metadata...', end=' ')
                metadata_obj = BibleMetaData(os.path.join(root, 'meta.json'))
                download_file(file_to_download, downloaded_file)
            finally:
                print('finished.')

        if 'usfm' in dirs:
            usfm_dir = os.path.join(root, 'usfm')

        # if we have everything, exit the loop
        if usfm_dir and metadata_obj:
            break

    # check for valid repository structure
    if not metadata_obj:
        print_error('Did not find meta.json in {}'.format(git_repo))
        sys.exit(1)

    if not usfm_dir:
        print_error('Did not find the usfm directory in {}'.format(git_repo))
        sys.exit(1)

    out_dir = out_template.format(domain, metadata_obj.slug, metadata_obj.lang)

    # walk through the usfm files
    usfm_files = glob(os.path.join(usfm_dir, '*.usfm'))
    for usfm_file in usfm_files:

        # read the file
        with codecs.open(usfm_file, 'r', 'utf-8') as in_file:
            book_text = in_file.read()

        # get the book id
        book_search = id_re.search(book_text)
        if not book_search:
            print_error('Book id not found in {}'.format(usfm_file))
            sys.exit(1)

        book_id = book_search.group(1)

        print('Beginning {}...'.format(book_id), end=' ')

        # get book versification info
        book = next((b for b in vrs if b.book_id == book_id), None)
        if not book:
            print_error('Book versification data was not found for "{}"'.format(book_id))
            sys.exit(1)

        # remove \s5 lines
        book_text = s5_re.sub('', book_text)

        # get the usfm for the book
        book.set_usfm(book_text)

        # do basic checks
        book.verify_chapters_and_verses(True)

        # get chunks for this book
        get_chunks(book)
        book.apply_chunks()

        # produces something like '01-GEN.usfm'
        book_file_name = '{0}-{1}.usfm'.format(str(book.number).zfill(2), book.book_id)
        print('Writing ' + book_file_name + '...', end=' ')
        write_file('{0}/{1}'.format(out_dir, book_file_name), book.usfm)

        meta = ['Bible: OT']
        if book.number > 39:
            meta = ['Bible: NT']
        books_published[book.book_id.lower()] = {'name': book.name,
                                                 'meta': meta,
                                                 'sort': str(book.number).zfill(2),
                                                 'desc': ''
                                                 }
        print('finished.')

    print('Writing status.json...', end=' ')
    status = {"slug": '{0}'.format(metadata_obj.slug.lower()),
              "name": metadata_obj.name,
              "lang": metadata_obj.lang,
              "date_modified": today,
              "books_published": books_published,
              "status": {"checking_entity": metadata_obj.checking_entity,
                         "checking_level": metadata_obj.checking_level,
                         "comments": metadata_obj.comments,
                         "contributors": metadata_obj.contributors,
                         "publish_date": today,
                         "source_text": metadata_obj.source_text,
                         "source_text_version": metadata_obj.source_text_version,
                         "version": metadata_obj.version
                         }
              }
    write_file('{0}/status.json'.format(out_dir), status, indent=2)
    print('finished.')

    print()
    print('Publishing to the API...')
    with api_publish(out_dir) as api:
        api.run()
    print('Finished publishing to the API.')

    # update the catalog
    print()
    print('Updating the catalogs...', end=' ')
    update_catalog()
    print('finished.')

    print_notice('Check {0} and do a git push'.format(out_dir))


def get_versification():
    """
    Get the versification file and parse it into book, chapter and verse information
    :return: list<Book>
    """
    global vrs_file, book_file

    # get the list of books
    books = json.loads(get_url(book_file))

    # get the versification file
    raw = get_url(vrs_file)
    lines = [l for l in raw.replace('\r', '').split('\n') if l and l[0:1] != '#']

    scheme = []
    for key, value in iter(books.items()):

        book = Book(key, value[0], int(value[1]))

        # find the key in the lines
        for line in lines:
            if line[0:3] == key:
                chapters = line[4:].split()
                for chapter in chapters:
                    parts = chapter.split(':')
                    book.chapters.append(Chapter(int(parts[0]), int(parts[1])))
                scheme.append(book)
                break

    return scheme


def get_re(text, regex):
    se = regex.search(text)
    if se:
        return se.group(1).strip()

    return None


def get_chunks(book):
    """
    :type book: Book
    """
    global chunk_url

    chunk_str = get_url(chunk_url.format(book.book_id.lower()))
    if not chunk_str:
        raise Exception('Could not load chunks for ' + book.book_id)

    for chunk in json.loads(chunk_str):
        book.chunks.append(Chunk(chunk))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r', '--gitrepo', dest='gitrepo', default=False,
                        required=True, help='Git repository where the source can be found.')

    parser.add_argument('-d', '--domain', dest='domain', choices=['udb', 'ulb', 'pdb'],
                        required=True, help='ulb, udb or pdb')

    args = parser.parse_args(sys.argv[1:])

    # prompt user to update meta.json
    print_notice('Check meta.json in the git repository and update the information if needed.')
    prompt('Press Enter to continue when ready...')

    try:
        print_ok('STARTING: ', 'importing USFM repository.')
        main(args.gitrepo, args.domain)
        print_ok('ALL FINISHED: ', 'importing USFM repository.')
        print_notice('Don\'t forget to notify the interested parties.')

    finally:
        # delete temp files
        if os.path.isdir(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
