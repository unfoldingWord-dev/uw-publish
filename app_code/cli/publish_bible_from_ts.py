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
import argparse
import codecs
import datetime
import json
import re
from glob import glob
from general_tools.file_utils import make_dir, unzip, load_json_object, write_file
from general_tools.print_utils import print_notice, print_ok, print_error
from general_tools.url_utils import join_url_parts, download_file
from uw.update_catalog import update_catalog
from app_code.bible.bible_classes import BibleMetaData, Bible, BibleStatus, BibleEncoder
from app_code.bible.content import Book, Chapter
import sys
import shutil
import os
from app_code.cli.api_publish import api_publish

if sys.version_info < (3, 0):
    prompt = raw_input
else:
    prompt = input

# remember this so we can delete it
download_dir = ''

out_template = '/var/www/vhosts/api.unfoldingword.org/httpdocs/{0}/txt/1/{1}'

verse_re = re.compile(r'\s+(\\v\s\d{1,3}[-,d]*)')
chapter_re = re.compile(r'^(\\c\s\d{1,3}[-,d]*)')
add_q_re = re.compile(r'\n\s+(\S+)')


def main(git_repo, tag, domain):
    global download_dir, out_template

    # clean up the git repo url
    if git_repo[-4:] == '.git':
        git_repo = git_repo[:-4]

    if git_repo[-1:] == '/':
        git_repo = git_repo[:-1]

    # initialize some variables
    today = ''.join(str(datetime.date.today()).rsplit('-')[0:3])  # str(datetime.date.today())
    download_dir = '/tmp/{0}'.format(git_repo.rpartition('/')[2])
    make_dir(download_dir)
    downloaded_file = '{0}/{1}.zip'.format(download_dir, git_repo.rpartition('/')[2])
    file_to_download = join_url_parts(git_repo, 'archive/' + tag + '.zip')
    manifest = None
    metadata_obj = None
    content_dir = ''
    usfm_file = None

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

        if 'manifest.json' in files:
            # read the manifest
            try:
                print('Reading the manifest...', end=' ')
                manifest = load_json_object(os.path.join(root, 'manifest.json'))
                content_dir = root

                # look for the usfm file for the whole book
                found_usfm = glob(os.path.join(content_dir, '*.usfm'))
                if len(found_usfm) == 1:
                    usfm_file = os.path.join(content_dir, found_usfm[0])
            finally:
                print('finished.')

        if 'meta.json' in files:
            # read the metadata
            try:
                print('Reading the metadata...', end=' ')
                metadata_obj = BibleMetaData(os.path.join(root, 'meta.json'))
            finally:
                print('finished.')

        # if we have everything, exit the loop
        if manifest and metadata_obj:
            break

    # check for valid repository structure
    if not manifest:
        print_error('Did not find manifest.json in {}'.format(git_repo))
        sys.exit(1)

    if not metadata_obj:
        print_error('Did not find meta.json in {}'.format(git_repo))
        sys.exit(1)

    # get the versification data
    print('Getting versification info...', end=' ')
    vrs = Bible.get_versification(metadata_obj.versification)  # type: list<Book>

    # get the book object for this repository
    book = next((b for b in vrs if b.book_id.lower() == manifest['project']['id']), None)  # type: Book
    if not book:
        print_error('Book versification data was not found for "{}"'.format(manifest['project']['id']))
        sys.exit(1)
    print('finished')

    if usfm_file:
        read_unified_file(book, usfm_file)

    else:
        read_chunked_files(book, content_dir, metadata_obj)

    # do basic checks
    print('Running USFM checks...', end=' ')
    book.verify_chapters_and_verses(True)
    if book.validation_errors:
        print_error('These USFM errors must be corrected before publishing can continue.')
        sys.exit(1)
    else:
        print('finished.')

    # insert paragraph markers
    print('Inserting paragraph markers...', end=' ')
    Bible.insert_paragraph_markers(book)
    print('finished.')

    # get chunks for this book
    print('Chunking the text...', end=' ')
    Bible.chunk_book(metadata_obj.versification, book)
    book.apply_chunks()
    print('finished.')

    # save the output
    out_dir = out_template.format(domain, metadata_obj.slug)

    # produces something like '01-GEN.usfm'
    book_file_name = '{0}-{1}.usfm'.format(str(book.number).zfill(2), book.book_id)
    print('Writing ' + book_file_name + '...', end=' ')
    write_file('{0}/{1}'.format(out_dir, book_file_name), book.usfm)
    print('finished.')

    # look for an existing status.json file
    print('Updating the status for {0}...'.format(metadata_obj.lang), end=' ')
    status_file = '{0}/status.json'.format(out_dir)
    if os.path.isfile(status_file):
        status = BibleStatus(status_file)
    else:
        status = BibleStatus()

    status.update_from_meta_data(metadata_obj)

    # add this book to the list of "books_published"
    status.add_book_published(book)

    # update the "date_modified"
    status.date_modified = today
    print('finished.')

    # save the status.json file
    print('Writing status.json...', end=' ')
    status_json = json.dumps(status, sort_keys=True, indent=2, cls=BibleEncoder)
    write_file(status_file, status_json)
    print('finished')

    # let the API know it is there
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


def reformat_usfm(usfm_in):
    global verse_re

    usfm_out = usfm_in.strip()

    # remove windows newlines
    usfm_out = usfm_out.replace('\r\n', '\n')

    # add \q where there are line breaks
    usfm_out = add_q_re.sub(r'\n\\q \1', usfm_out)

    # start each verse on a new line
    usfm_out = verse_re.sub(r'\n\1', usfm_out)

    return usfm_out


def remove_chapter_markers(usfm_in):
    global chapter_re

    return chapter_re.sub(r'', usfm_in)


def read_chunked_files(book, content_dir, metadata_obj):

    print('Reading chapter USFM files...', end=' ')
    for i in range(0, len(book.chapters) + 1):

        # get the directory for this chapter
        chapter_dir = os.path.join(content_dir, str(i).zfill(2))
        if not os.path.isdir(chapter_dir):
            print_error('Did not find directory for chapter {}.'.format(i))
            sys.exit(1)

        # directory 00 contains the translated book title
        if i == 0:
            file_name = os.path.join(chapter_dir, 'title.txt')
            if not os.path.isfile(file_name):
                print_error('Did not find file "{}".'.format(file_name))
                sys.exit(1)

            with codecs.open(file_name, 'r', 'utf-8-sig') as in_file:
                translated_name = in_file.read()

            header_usfm = Bible.get_header_text()
            header_usfm = header_usfm.replace('{BOOK_CODE}', book.book_id)
            header_usfm = header_usfm.replace('{BIBLE_NAME}', metadata_obj.name)
            header_usfm = header_usfm.replace('{BOOK_NAME_SHORT}', translated_name)
            header_usfm = header_usfm.replace('{BOOK_NAME_LONG}', translated_name)

            book.name = translated_name
            book.header_usfm = header_usfm

        else:
            # other directories will have the chunk files for the chapter
            chapter = next((c for c in book.chapters if c.number == i), None)  # type: Chapter

            chunk_list = [f for f in os.listdir(chapter_dir) if re.search(r'[0-1]?[0-9][0-9]\.txt$', f)]
            chunk_list.sort()
            for chunk_file in chunk_list:

                # skip the junk chunk in the last chapter
                if chunk_file == '00.txt' or chunk_file == '000.txt':
                    continue

                file_name = os.path.join(chapter_dir, chunk_file)
                if not os.path.isfile(file_name):
                    print_error('Did not find file "{}".'.format(file_name))
                    sys.exit(1)

                with codecs.open(file_name, 'r', 'utf-8-sig') as in_file:
                    chunk_usfm = in_file.read()

                chapter.usfm += reformat_usfm(remove_chapter_markers(chunk_usfm)) + "\n"

    book.build_usfm_from_chapters()
    print('finished.')


def read_unified_file(book, usfm_file):

    # read the file
    print('Reading {}...'.format(usfm_file), end=' ')
    with codecs.open(usfm_file, 'r', 'utf-8') as in_file:
        book_text = in_file.read()

    # remove \s5
    s5_re = re.compile(r'\\s5\s*')
    book_text = s5_re.sub('', book_text)

    # get the usfm for the book
    book.set_usfm(reformat_usfm(book_text))
    print('finished')


if __name__ == '__main__':
    print()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r', '--gitrepo', dest='gitrepo', default=False,
                        required=True, help='Git repository where the source can be found.')
    parser.add_argument('-t', '--tag', dest='tag', default='master',
                        required=False, help='Branch or tag to use as the source. Default is master.')
    parser.add_argument('-d', '--domain', dest='domain', choices=['udb', 'ulb', 'pdb'],
                        required=True, help='ulb, udb or pdb')

    args = parser.parse_args(sys.argv[1:])

    # prompt user to update meta.json
    print_notice('Check meta.json in the git repository and update the information if needed.')
    prompt('Press Enter to continue when ready...')

    try:
        print_ok('STARTING: ', 'publishing Bible repository.')
        main(args.gitrepo, args.tag, args.domain)
        print_ok('ALL FINISHED: ', 'publishing Bible repository.')
        print_notice('Don\'t forget to notify the interested parties.')

    finally:
        # delete temp files
        if os.path.isdir(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
