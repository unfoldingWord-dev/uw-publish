from __future__ import print_function, unicode_literals
import argparse
import codecs
import os
import sys
from glob import glob
import re
from general_tools.print_utils import print_ok, print_error
from app_code.bible.bible_classes import Bible
from app_code.bible.content import Book

if sys.version_info < (3, 0):
    prompt = raw_input
else:
    prompt = input

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

id_re = re.compile(r'\\id[\u00A0\s](\w{3}).*')
s5_re = re.compile(r'\\s5\s*')


def main(directory_to_check, versification):
    """

    :param str|unicode directory_to_check:
    :param str|unicode versification:
    """

    # get the versification data
    vrs = Bible.get_versification(versification)  # type: list<Book>

    # walk through the usfm files
    patterns = ['*.usfm', '*.sfm', '*.SFM']
    usfm_files = []
    for pattern in patterns:
        usfm_files.extend(glob(os.path.join(directory_to_check, pattern)))

    errors_found = False
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
        if book.validation_errors:
            errors_found = True

        print('finished.')

    # stop if errors were found
    if errors_found:
        print_error('These USFM errors must be corrected before publishing can continue.')
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-d', '--directory', dest='directory', default=False, required=True,
                        help='The directory to check.')
    parser.add_argument('-v', '--versification', dest='versification', default='ufw', required=False,
                        help='Versification system - current options are "ufw" (unfoldingWord) and "rsc" (Russian)')

    args = parser.parse_args(sys.argv[1:])

    print_ok('STARTING: ', 'validating USFM files.')
    main(args.directory, args.versification)
    print_ok('ALL FINISHED: ', 'validating USFM files.')
