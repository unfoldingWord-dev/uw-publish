from __future__ import print_function, unicode_literals
import re
from general_tools.print_utils import print_error
from bible_classes import USFM


class Book(object):
    verse_re = re.compile(r'(\\v\s*[0-9\-]*\s+)', re.UNICODE)
    chapter_re = re.compile(r'(\\c\s*[0-9]*\s*\n)', re.UNICODE)
    tag_re = re.compile(r'\s(\\\S+)\s', re.UNICODE)
    bad_tag_re = re.compile(r'(\S\\\S+)\s', re.UNICODE)
    tag_exceptions = ('\\f*', '\\fe*', '\\qs*')

    def __init__(self, book_id, name, number):
        """
        :type book_id: str
        :type name: str
        :type number: int
        """
        self.book_id = book_id       # type: str
        self.name = name             # type: str
        self.number = number         # type int
        self.chapters = []           # type: list<Chapter>
        self.chunks = []             # type: list<Chunk>
        self.dir_name = str(number).zfill(2) + '-' + book_id  # type: str
        self.usfm = None             # type: str
        self.validation_errors = []  # type: list<str>
        self.header_usfm = ''        # type: str

    def number_string(self):
        return str(self.number).zfill(2)

    def set_usfm(self, new_usfm):
        self.usfm = new_usfm.replace('\r\n', '\n')

    def build_usfm_from_chapters(self):
        self.usfm = self.header_usfm

        self.chapters.sort(key=lambda c: c.number)
        for chapter in self.chapters:
            self.usfm += "\n\n\\c {0}\n{1}".format(chapter.number, chapter.usfm)

    def verify_chapters_and_verses(self, same_line=False):

        if same_line:
            print('Verifying ' + self.book_id + '... ', end=' ')
        else:
            print('Verifying ' + self.book_id)

        # check for git conflicts
        if '<<<< HEAD' in self.usfm:
            self.append_error('There is a Git conflict header in ' + self.book_id)

        # split into chapters
        self.check_chapters(self.chapter_re.split(self.usfm))

    def verify_usfm_tags(self, same_line=False):

        if same_line:
            print('Checking USFM in ' + self.book_id + '... ', end=' ')
        else:
            print('Checking USFM in ' + self.book_id)

        # split into chapters
        chapters_usfm = self.chapter_re.split(self.usfm)
        current_chapter = '\c 0'

        for chapter_usfm in chapters_usfm:
            if chapter_usfm[0:2] == '\c':
                current_chapter = chapter_usfm.strip()
            else:
                # get all tags
                matches = re.findall(self.tag_re, chapter_usfm)
                for match in matches:
                    if not USFM.is_valid_tag(match):

                        # check the exceptions
                        if not match.startswith(self.tag_exceptions):
                            self.append_error('Invalid USFM tag in ' + current_chapter + ': ' + match)

                # check for bad tags
                matches = re.findall(self.bad_tag_re, chapter_usfm)
                for match in matches:

                    # check the exceptions
                    if not match.endswith(self.tag_exceptions):
                        self.append_error('Invalid USFM tag in ' + current_chapter + ': ' + match)

    def check_chapters(self, blocks):

        self.header_usfm = ''

        # find the first chapter marker, should be the second block
        # the first block should be everything before the first chapter marker
        current_index = 0
        while blocks[current_index][:2] != '\c':
            self.header_usfm += blocks[current_index].rstrip()
            current_index += 1

        # loop through the blocks
        while current_index < len(blocks):

            # parse the chapter number
            test_num = blocks[current_index][3:].strip()
            if not test_num.isdigit():
                self.append_error('Invalid chapter number, ' + self.book_id + ' "' + test_num + '"')

            # compare this chapter number to the numbers from the versification file
            try:
                chapter_num = int(test_num)
            except ValueError:
                self.append_error('Invalid chapter number, ' + self.book_id + ' "' + blocks[current_index] + '"')
                continue

            found_chapter = next((c for c in self.chapters if c.number == chapter_num), None)  # type: Chapter
            if not found_chapter:
                self.append_error('Invalid chapter number, ' + self.book_id + ' "' + test_num + '"')

            else:
                found_chapter.found = True

                # make sure there is a chapter body
                if current_index + 1 >= len(blocks):
                    self.append_error('No verses found in ' + self.book_id + ' ' + str(found_chapter.number))

                else:
                    # split the chapter text into verses
                    self.check_verses(found_chapter, self.verse_re.split(blocks[current_index + 1]))

                    # remember for later
                    found_chapter.usfm = blocks[current_index] + '\n' + blocks[current_index + 1] + '\n'

            # increment the counter
            current_index += 2

    def check_verses(self, found_chapter, verse_blocks):

        last_verse = 0
        processed_verses = []

        # go to the first verse marker
        current_cv_index = 0
        while current_cv_index < len(verse_blocks) and verse_blocks[current_cv_index][:2] != '\\v':
            current_cv_index += 1

        # are all the verse markers missing?
        if current_cv_index >= len(verse_blocks):
            self.append_error('All verse markers are missing for ' + self.book_id + ' ' + str(found_chapter.number))
            return

        # verses should be sequential, starting at 1 and ending at found_chapter.expected_max_verse_number
        while current_cv_index < len(verse_blocks):

            # parse the verse number
            test_num = verse_blocks[current_cv_index][3:].strip()

            # is this a verse bridge?
            if '-' in test_num:
                nums = test_num.split('-')
                if len(nums) != 2 or not nums[0].strip().isdigit() or not nums[1].strip().isdigit():
                    self.append_error('Invalid verse bridge, ' + self.book_id + ' ' +
                                      str(found_chapter.number) + ':' + test_num)

                else:
                    for bridge_num in range(int(nums[0].strip()), int(nums[1].strip()) + 1):
                        last_verse = self.check_this_verse(found_chapter, bridge_num, last_verse, processed_verses)

                    current_cv_index += 2
            else:
                if not test_num.isdigit():

                    # the verse number isn't a number
                    self.append_error('Invalid verse number, ' + self.book_id + ' ' +
                                      str(found_chapter.number) + ':' + test_num)

                else:
                    verse_num = int(test_num)
                    last_verse = self.check_this_verse(found_chapter, verse_num, last_verse, processed_verses)

                current_cv_index += 2

        # are there verses missing from the end
        if last_verse < found_chapter.expected_max_verse_number:
            self.append_error('Verses ' + str(last_verse + 1) + ' through ' +
                              str(found_chapter.expected_max_verse_number) + ' for ' + self.book_id + ' ' +
                              str(found_chapter.number) + ' are missing.')

    def check_this_verse(self, found_chapter, verse_num, last_verse, processed_verses):

        # is this verse number too large?
        if verse_num > found_chapter.expected_max_verse_number:
            self.append_error('Invalid verse number, ' + self.book_id + ' ' +
                              str(found_chapter.number) + ':' + str(verse_num))

        # look for gaps in the verse numbers
        while verse_num > last_verse + 1 and last_verse < found_chapter.expected_max_verse_number:
            # there is a verse missing
            self.append_error('Verse not found, ' + self.book_id + ' ' +
                              str(found_chapter.number) + ':' + str(last_verse + 1))
            last_verse += 1

        # look for out-of-order verse numbers
        if verse_num < last_verse:
            self.append_error('Verse out-of-order, ' + self.book_id + ' ' +
                              str(found_chapter.number) + ':' + str(verse_num))

        # look for duplicate verse numbers
        if verse_num == last_verse or verse_num in processed_verses:
            self.append_error('Duplicate verse, ' + self.book_id + ' ' +
                              str(found_chapter.number) + ':' + str(verse_num))

        # remember for next time
        if verse_num > last_verse:
            last_verse = verse_num

        processed_verses.append(verse_num)

        return last_verse

    def append_error(self, message, prefix='** '):

        print_error(prefix + message)
        self.validation_errors.append(message)

    def apply_chunks(self):
        for chap in self.chapters:
            chap.apply_chunks([c for c in self.chunks if c.chapter_num == chap.number])

        new_usfm = ''
        for chap in self.chapters:
            new_usfm += chap.usfm + '\n'

        # extra space between header and first chapter
        self.usfm = self.header_usfm + '\n\n' + new_usfm


class Chapter(object):
    def __init__(self, number, expected_max_verse_number):
        """
        :type number: int
        :type expected_max_verse_number: int
        """
        self.number = number  # type: int
        self.expected_max_verse_number = expected_max_verse_number  # type: int
        self.missing_verses = []  # type: list<int>
        self.found = False  # type: bool
        self.usfm = ''

    def apply_chunks(self, chunks):
        """

        :type chunks: list<Chunk>
        """
        previous_line = ''

        # insert the first marker now
        newlines = ['\n\\s5', ]
        i = 0

        for line in self.usfm.splitlines():
            if line in ['', ' ', '\n']:
                continue

            if i < len(chunks):

                # we already inserted the beginning marker
                if chunks[i].first_verse == 1:
                    i += 1

                if i < len(chunks):
                    verse_search = re.search(r'\\v {0}[\s-]'.format(chunks[i].first_verse), line)
                    if verse_search:

                        # insert before \p, not after
                        if previous_line == '\\p':
                            newlines.insert(len(newlines) - 1, '\n\\s5')
                        else:
                            newlines.append('\n\\s5')

                        i += 1

            newlines.append(line)
            previous_line = line

        self.usfm = '\n'.join(newlines)


class Chunk(object):
    def __init__(self, chapter, first_verse):
        self.chunk_id = str(chapter).zfill(2) + '-' + str(first_verse).zfill(2)
        self.chapter_num = chapter
        self.first_verse = first_verse

    def __str__(self):
        return self.chunk_id
