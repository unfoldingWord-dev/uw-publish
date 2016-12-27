from __future__ import print_function, unicode_literals
import codecs
import os
from unittest import TestCase
from app_code.bible.content import Book


class TestUSFMChecks(TestCase):

    def test_invalid_usfm_tags(self):

        resources_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')
        test_file = os.path.join(resources_dir, 'checks01.usfm')

        # read the file
        with codecs.open(test_file, 'r', 'utf-8') as in_file:
            book_usfm = in_file.read()

        book = Book.create_book('PHP')  # type: Book
        book.set_usfm(book_usfm)

        # run the checks
        book.verify_usfm_tags()
        problems = book.validation_errors

        # should detect a verse with no text
        self.assertIn('Verse tag without text in \\c 2: "\\v 1"', problems)
        self.assertIn('Verse tag without text in \\c 2: "\\v 2"', problems)

    def test_chapter_and_verse_problems(self):

        resources_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')
        test_file = os.path.join(resources_dir, 'checks01.usfm')

        # read the file
        with codecs.open(test_file, 'r', 'utf-8') as in_file:
            book_usfm = in_file.read()

        book = Book.create_book('PHP')  # type: Book
        book.set_usfm(book_usfm)

        # should contain \s5 tags
        self.assertIn('\s5\n', book.usfm)

        # should not contain \s5 tags after cleaning
        book.clean_usfm()
        self.assertNotIn('\s5\n', book.usfm)

        # run the checks
        book.verify_chapters_and_verses()
        problems = book.validation_errors

        # should detect a merge conflict
        self.assertIn('There is 1 Git conflict in PHP', problems)
