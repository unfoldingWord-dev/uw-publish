#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#    This file imports the source text for ULB and UDB from https://github.com/Door43/ulb-en/archive/master.zip
#    or https://github.com/Door43/udb-en/archive/master.zip. The source is expected to be broken down into one
#    chapter per file.
#
#    Copyright (c) 2014, 2016 unfoldingWord
#    http://creativecommons.org/licenses/MIT/
#    See LICENSE file for details.
#
#    Contributors:
#    Jesse Griffin <jesse@distantshores.org>
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

from general_tools.print_utils import print_warning
from uw.update_catalog import update_catalog
from app_code.bible.content import Book, Chapter, Chunk
from general_tools.file_utils import unzip, write_file
from general_tools.url_utils import download_file, get_url
from app_code.cli.api_publish import api_publish

# remember these so we can delete them
downloaded_file = ''
unzipped_dir = ''

out_template = '/var/www/vhosts/api.unfoldingword.org/httpdocs/{0}/txt/1/{0}-{1}'

s5_re = re.compile(r'\\s5\s*')
nl_re = re.compile(r'\n{2,}')

# TODO: change these to point to the API when it is available
api_root = 'https://raw.githubusercontent.com/unfoldingWord-dev/uw-api/develop/static'
vrs_file = api_root + '/versification/ufw/ufw.vrs'
book_file = api_root + '/versification/ufw/books.json'
chunk_url = api_root + '/versification/ufw/chunks/{0}.json'


def main(resource, lang, slug, name, checking, contrib, ver, check_level,
         comments, source):

    global downloaded_file, unzipped_dir, out_template

    vrs = get_versification()  # type: list<Book>

    today = ''.join(str(datetime.date.today()).rsplit('-')[0:3])
    downloaded_file = '/tmp/{0}'.format(resource.rpartition('/')[2])
    unzipped_dir = '/tmp/{0}'.format(resource.rpartition('/')[2].strip('.zip'))
    out_dir = out_template.format(slug, lang)

    if not os.path.isfile(downloaded_file):
        download_file(resource, downloaded_file)

    unzip(downloaded_file, unzipped_dir)

    books_published = {}
    there_were_errors = False

    for root, dirs, files in os.walk(unzipped_dir):

        # only usfm files
        files = [f for f in files if f[-3:].lower() == 'sfm']

        if not len(files):
            continue

        # there are usfm files, which book is this?
        test_dir = root.rpartition('/')[2]
        book = next((b for b in vrs if b.dir_name == test_dir), None)  # type: Book

        if book:
            book_text = ''
            files.sort()

            for usfm_file in files:
                with codecs.open(os.path.join(root, usfm_file), 'r', 'utf-8') as in_file:
                    book_text += in_file.read() + '\n'

            # remove superfluous line breaks
            book_text = nl_re.sub('\n', book_text)

            # remove \s5 lines
            book_text = s5_re.sub('', book_text)

            book.set_usfm(book_text)

            # do basic checks
            book.verify_usfm_tags()
            book.verify_chapters_and_verses()
            if len(book.validation_errors) > 0:
                there_were_errors = True

            if there_were_errors:
                continue

            # get chunks for this book
            get_chunks(book)
            book.apply_chunks()

            # produces something like '01-GEN.usfm'
            book_file_name = '{0}-{1}.usfm'.format(str(book.number).zfill(2), book.book_id)
            print('Writing ' + book_file_name)
            write_file('{0}/{1}'.format(out_dir, book_file_name), book.usfm)

            meta = ['Bible: OT']
            if book.number > 39:
                meta = ['Bible: NT']
            books_published[book.book_id.lower()] = {'name': book.name,
                                                     'meta': meta,
                                                     'sort': str(book.number).zfill(2),
                                                     'desc': ''
                                                     }

    if there_were_errors:
        print_warning('There are errors you need to fix before continuing.')
        exit()

    source_ver = ver
    if '.' in ver:
        source_ver = ver.split('.')[0]
    status = {"slug": '{0}-{1}'.format(slug.lower(), lang),
              "name": name,
              "lang": lang,
              "date_modified": today,
              "books_published": books_published,
              "status": {"checking_entity": checking,
                         "checking_level": check_level,
                         "comments": comments,
                         "contributors": contrib,
                         "publish_date": today,
                         "source_text": source,
                         "source_text_version": source_ver,
                         "version": ver
                         }
              }
    write_file('{0}/status.json'.format(out_dir), status)

    print('Publishing to the API...')
    with api_publish(out_dir) as api:
        api.run()
    print('Finished publishing to the API.')

    # update the catalog
    print()
    print('Updating the catalogs...', end=' ')
    update_catalog()
    print('finished.')

    print('Check {0} and do a git push'.format(out_dir))


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

    chunks_obj = json.loads(chunk_str)

    # chunk it
    for chapter in chunks_obj:
        for first_verse in chapter['first_verses']:
            book.chunks.append(Chunk(chapter['chapter'], first_verse))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r', '--resource', dest="resource", default=False,
                        required=True, help="URL of zip file.")
    parser.add_argument('-l', '--lang', dest="lang", default=False,
                        required=True, help="Language code of resource.")
    parser.add_argument('-s', '--slug', dest="slug", default=False,
                        required=True, help="Slug of resource name (e.g. NIV).")
    parser.add_argument('-n', '--name', dest="name", default=False,
                        required=True, help="Name (e.g. 'New International Version').")
    parser.add_argument('-c', '--checking', dest="checking", default=False,
                        required=True, help="Checking entity.")
    parser.add_argument('-t', '--translators', dest="contrib", default=False,
                        required=True, help="Contributing translators.")
    parser.add_argument('-v', '--version', dest="version", default=False,
                        required=True, help="Version of resource.")
    parser.add_argument('-e', '--check_level', dest="check_level", default=3,
                        required=False, help="Checking level of the resource.")
    parser.add_argument('-m', '--comments', dest="comments", default="",
                        required=False, help="Comments on the resource.")
    parser.add_argument('-o', '--source', dest="source", default="en",
                        required=False, help="Source language code.")

    args = parser.parse_args(sys.argv[1:])

    try:
        main(args.resource, args.lang, args.slug, args.name, args.checking,
             args.contrib, args.version, args.check_level, args.comments, args.source)
    finally:
        # delete temp files
        if os.path.isfile(downloaded_file):
            os.remove(downloaded_file)

        if os.path.isdir(unzipped_dir):
            shutil.rmtree(unzipped_dir, ignore_errors=True)
