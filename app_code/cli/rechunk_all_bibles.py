from __future__ import unicode_literals, print_function
import codecs
import json
import os
from glob import glob
import sys
import re
from general_tools.file_utils import write_file
from general_tools.print_utils import print_notice, print_error, print_ok
from uw.update_catalog import update_catalog
from app_code.bible.bible_classes import Bible
from app_code.bible.content import Book
from app_code.cli.api_publish import api_publish

id_re = re.compile(r'\\id[\u00A0\s](\w{3}).*')
s5_re = re.compile(r'\\s5[\u00A0\s]*')


def get_source_directories():
    domains = ['pdb', 'ulb', 'udb']
    api_source_dir = '/var/www/vhosts/api.unfoldingword.org/httpdocs/{0}/txt/1'
    directories = []

    for domain in domains:
        domain_dir = api_source_dir.format(domain)
        subdirectories = next(os.walk(domain_dir))[1]
        for subdirectory in subdirectories:
            directories.append(os.path.join(domain_dir, subdirectory))

    return directories


def rechunk_this_one(api_directory):
    global id_re, s5_re

    print_notice('Processing {}'.format(api_directory))

    # read the status.json file
    with codecs.open(os.path.join(api_directory, 'status.json'), 'r', 'utf-8-sig') as in_file:
        status = json.loads(in_file.read())

    # determine versification
    if status['lang'] == 'ru':
        versification = 'rsc'

    elif status['lang'] == 'hi' or status['lang'] == 'sr-Latn' or status['lang'] == 'hu' or status['lang'] == 'ta':
        versification = 'ufw-odx'

    elif status['lang'] == 'bn':
        versification = 'ufw-bn'

    elif status['lang'] == 'ar':
        versification = 'avd'

    elif status['lang'] == 'kn':
        versification = 'ufw-rev'

    else:
        versification = 'ufw'

    versification_data = Bible.get_versification(versification)  # type: list<Book>

    # remove all .sig files
    for f in os.listdir(api_directory):
        if f.endswith('.sig'):
            os.remove(os.path.join(api_directory, f))

    # rechunk files in this directory
    usfm_files = glob(os.path.join(api_directory, '*.usfm'))
    errors_found = False
    for usfm_file in usfm_files:

        if usfm_file.endswith('LICENSE.usfm'):
            continue

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
        book = next((b for b in versification_data if b.book_id == book_id), None)
        if not book:
            print_error('Book versification data was not found for "{}"'.format(book_id))
            sys.exit(1)

        # remove \s5 lines
        book_text = s5_re.sub('', book_text)

        # get the usfm for the book
        book.set_usfm(book_text)

        # do basic checks
        book.verify_chapters_and_verses(True)
        if book.validation_errors:
            errors_found = True

        # get chunks for this book
        Bible.chunk_book(versification, book)
        book.apply_chunks()

        # produces something like '01-GEN.usfm'
        book_file_name = '{0}-{1}.usfm'.format(str(book.number).zfill(2), book.book_id)
        print('Writing ' + book_file_name + '...', end=' ')
        write_file(usfm_file, book.usfm)

        print('finished.')

    if errors_found:
        print_error('These USFM errors must be corrected before publishing can continue.')
        sys.exit(1)

    # rebuild source for tS
    print()
    print('Publishing to the API...')
    with api_publish(api_directory) as api:
        api.run()
    print('Finished publishing to the API.')

    # update the catalog
    print()
    print('Updating the catalogs...', end=' ')
    update_catalog()
    print('finished.')


if __name__ == '__main__':

    print_ok('STARTING: ', 're-chunking all Bibles.')

    source_directories = get_source_directories()

    for source_directory in source_directories:
        rechunk_this_one(source_directory)

    print_ok('ALL FINISHED: ', 're-chunking all Bibles.')
