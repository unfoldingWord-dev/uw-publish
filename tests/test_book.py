from __future__ import print_function, unicode_literals

import codecs
import os
import sys
from unittest import TestCase
from app_code.bible.content import Book

if sys.version_info < (3, 0):
    from_char = unicode
else:
    from_char = str


class TestBook(TestCase):
    def test_set_usfm_with_nbsp_in_tags(self):
        """
        Tests for non-breaking space character (160 or \u00A0) being removed from USFM tags
        """
        resources_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')
        test_file = os.path.join(resources_dir, 'nbsp.usfm')

        # read the file
        with codecs.open(test_file, 'r', 'utf-8') as in_file:
            book_text = in_file.read()

        # verify nbsp is present
        self.assertEqual(160, ord(book_text[3:4]))
        self.assertEqual(823, book_text.count(from_char('\u00A0')))

        # set the book text with the USFM read from the file
        book = Book('ROM', 'Romans', 46)
        book.set_usfm(book_text)

        # verify nbsp has been removed from USFM tags
        test_text = book.usfm
        self.assertEqual(32, ord(test_text[3:4]))
        self.assertEqual(71, test_text.count(from_char('\u00A0')))
