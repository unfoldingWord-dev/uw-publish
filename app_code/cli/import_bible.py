#!/usr/bin/env python2
# -*- coding: utf8 -*-
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
import zipfile
from app_code.bible.content import Book, Chapter, Chunk

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2


# remember these so we can delete them
downloaded_file = ''
unzipped_dir = ''

chunk_url = 'https://api.unfoldingword.org/ts/txt/2/{0}/en/ulb/chunks.json'
out_template = '/var/www/vhosts/api.unfoldingword.org/httpdocs/{0}/txt/1/{0}-{1}'

s5_re = re.compile(r'\\s5\s*')
nl_re = re.compile(r'\n{2,}')

# TODO: change these to point to the API when it is available
vrs_file = 'https://raw.githubusercontent.com/unfoldingWord-dev/uw-api/develop/static/versification/ufw/ufw.vrs'
book_file = 'https://raw.githubusercontent.com/unfoldingWord-dev/uw-api/develop/static/versification/ufw/books-en.json'


def main(resource, lang, slug, name, checking, contrib, ver, check_level,
         comments, source):

    global downloaded_file, unzipped_dir, out_template

    vrs = get_versification()  # type: list<Book>

    today = ''.join(str(datetime.date.today()).rsplit('-')[0:3])
    downloaded_file = '/tmp/{0}'.format(resource.rpartition('/')[2])
    unzipped_dir = '/tmp/{0}'.format(resource.rpartition('/')[2].strip('.zip'))
    out_dir = out_template.format(slug, lang)

    if not os.path.isfile(downloaded_file):
        get_zip(resource, downloaded_file)

    unzip(downloaded_file, unzipped_dir)

    books_published = {}

    for root, dirs, files in os.walk(unzipped_dir):

        # only usfm files
        files = [f for f in files if f[-3:].lower() == 'sfm']

        if not len(files):
            continue

        # there are usfm files, which book is this?
        test_dir = root.rpartition('/')[2]
        book = next((b for b in vrs if b.dir_name == test_dir), None)

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
            book.verify_chapters_and_verses()

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
    write_json('{0}/status.json'.format(out_dir), status)
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


def get_url(url):
    request = urllib2.urlopen(url)
    response = request.read()
    request.close()
    return response


def get_zip(url, outfile):
    print('Getting ZIP')
    # noinspection PyBroadException
    try:
        request = urllib2.urlopen(url)
    except:
        print('    => ERROR retrieving %s\nCheck the URL' % url)
        sys.exit(1)
    with open(outfile, 'wb') as fp:
        shutil.copyfileobj(request, fp)


def unzip(source, dest):
    with zipfile.ZipFile(source) as zf:
        zf.extractall(dest)


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
        book.chunks.append(Chunk(chunk['id']))


def write_json(out_file, p):
    """
    Simple wrapper to write a file as JSON.
    :param out_file:
    :param p:
    """
    make_dir(out_file.rsplit('/', 1)[0])
    f = codecs.open(out_file, 'w', encoding='utf-8')
    f.write(json.dumps(p, sort_keys=True))
    f.close()


def write_file(f, content):
    make_dir(f.rpartition('/')[0])
    out = codecs.open(f, encoding='utf-8', mode='w')
    out.write(content)
    out.close()


def make_dir(d):
    if not os.path.exists(d):
        os.makedirs(d, 0o755)


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
