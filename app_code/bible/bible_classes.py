from __future__ import unicode_literals
import codecs
import json
import os
from datetime import datetime
from json import JSONEncoder
from general_tools.file_utils import load_json_object
from general_tools.url_utils import get_url
from app_code.bible import bible_paragraphs
from app_code.bible.content import Book, Chapter, Chunk
from app_code.util import app_utils


class BibleMetaData(object):
    def __init__(self, file_name=None):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param str file_name: The name of a file to deserialize into a BibleMetaData object
        """
        # deserialize
        if file_name:
            if os.path.isfile(file_name):
                self.__dict__ = load_json_object(file_name)
                if 'versification' not in self.__dict__:
                    self.versification = 'ufw'
            else:
                raise IOError('The file {0} was not found.'.format(file_name))
        else:
            self.lang = ''
            self.name = ''
            self.slug = ''
            self.checking_entity = ''
            self.checking_level = '1'
            self.comments = ''
            self.contributors = ''
            self.publish_date = datetime.today().strftime('%Y-%m-%d')
            self.source_text = ''
            self.source_text_version = ''
            self.version = ''
            self.versification = 'ufw'


class Bible(object):

    # do not access this directly, use Bible.get_usfm_data
    usfm_data = None

    @staticmethod
    def get_versification(versification):
        """
        Get the versification file and parse it into book, chapter and verse information
        :return: list<Book>
        """

        # TODO: change these to point to the API when it is available
        api_root = 'https://raw.githubusercontent.com/unfoldingWord-dev/uw-api/develop/static'
        vrs_file = api_root + '/versification/{0}/{0}.vrs'
        book_file = api_root + '/versification/{0}/books.json'

        # get the list of books
        books = json.loads(get_url(book_file.format(versification)))

        # get the versification file
        raw = get_url(vrs_file.format(versification))
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

    @staticmethod
    def get_header_text():
        file_name = os.path.join(app_utils.get_static_dir(), 'bible-header.usfm')
        with codecs.open(file_name, 'r', encoding='utf-8') as in_file:
            return in_file.read()

    @staticmethod
    def chunk_book(versification, book):
        """
        :param versification:
        :type book: Book
        """

        # TODO: change these to point to the API when it is available
        api_root = 'https://raw.githubusercontent.com/unfoldingWord-dev/uw-api/develop/static'
        chunk_url = api_root + '/versification/{0}/chunks/{1}.json'

        chunk_str = get_url(chunk_url.format(versification, book.book_id.lower()))
        if not chunk_str:
            raise Exception('Could not load chunks for ' + book.book_id)

        # chunk it
        for chapter in json.loads(chunk_str):
            for first_verse in chapter['first_verses']:
                book.chunks.append(Chunk(chapter['chapter'], first_verse))

    @staticmethod
    def insert_paragraph_markers(book):

        paragraph_list = bible_paragraphs.bible_paragraphs

        chapter_data = next(p for p in paragraph_list if p['usfm_id'] == book.book_id)['chapters']
        for chapter in book.chapters:

            # check if there are already paragraph markers
            if '\n\\p' in chapter.usfm:
                continue

            # get the verses that begin paragraphs
            paragraph_verses = next(c['paragraph_before'] for c in chapter_data if int(c['number']) == chapter.number)

            for verse in paragraph_verses:
                chapter.usfm = chapter.usfm.replace('\\v {0} '.format(verse), '\n\\p\n\\v {0} '.format(verse))

    @staticmethod
    def get_usfm_data():

        if not Bible.usfm_data:
            # TODO: change these to point to the API when it is available
            api_root = 'https://raw.githubusercontent.com/unfoldingWord-dev/uw-api/develop/static'
            usfm_data_file = api_root + '/versification/ufw/books-en.json'
            Bible.usfm_data = load_json_object(usfm_data_file)

        return Bible.usfm_data


class BibleStatus(object):
    def __init__(self, file_name=None):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param unicode file_name: The name of a file to deserialize into a BibleMetaData object
        """
        # deserialize
        if file_name:
            if os.path.isfile(file_name):
                self.__dict__ = load_json_object(file_name)
            else:
                raise IOError('The file {0} was not found.'.format(file_name))
        else:
            self.slug = ''  # like "{0}-{1}".format(domain, lang) = "ulb-lpx"
            self.name = ''  # like "Unlocked Literal Bible - Lopit"
            self.lang = ''  # like "lpx"
            self.date_modified = ''  # like "20160417"
            self.status = {"checking_entity": '',  # like "Translation Team"
                           "checking_level": '1',
                           "comments": '',
                           "contributors": '',
                           "publish_date": '',  # like "20160417"
                           "source_text": 'en',
                           "source_text_version": '2',
                           "version": '2.1'  # this is source_text_version + '.1' = 2.1 or 2.1.1
                           }
            self.books_published = {}

    def update_from_meta_data(self, metadata):
        """
        Initialize from a BibleMetaData object
        :param BibleMetaData metadata:
        :return:
        """
        self.slug = metadata.slug
        self.name = metadata.name
        self.lang = metadata.lang
        self.status['checking_entity'] = metadata.checking_entity
        self.status['checking_level'] = metadata.checking_level
        self.status['comments'] = metadata.comments
        self.status['contributors'] = metadata.contributors
        self.status['publish_date'] = metadata.publish_date
        self.status['source_text'] = metadata.source_text
        self.status['source_text_version'] = metadata.source_text_version
        self.status['version'] = metadata.version

    def add_book_published(self, book):
        """
        Adds a book to the published list, if it isn't already there
        :param Book book:
        :return:
        """
        book_id_lower = book.book_id.lower()
        if book_id_lower in self.books_published:
            return

        book_info = {'desc': '', 'meta': [], 'name': book.name, 'sort': book.number_string()}
        book_info['meta'].append('Bible: OT' if book.number < 40 else 'Bible: NT')
        self.books_published[book_id_lower] = book_info


class BibleEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
