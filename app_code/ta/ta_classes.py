# -*- coding: utf8 -*-

from __future__ import print_function, unicode_literals
import codecs
import os
import re
from datetime import datetime
import time
from json import JSONEncoder
import yaml
from general_tools.file_utils import load_json_object
from general_tools.print_utils import print_error


class TAEncoder(JSONEncoder):
    def default(self, o):
        """
        :param TAManual o:
        :return:
        """
        return o.to_serializable()


class TAStatus(object):
    def __init__(self, file_name=None):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param str file_name: The name of a file to deserialize into a TAStatus object
        """
        # deserialize
        if file_name:
            if os.path.isfile(file_name):
                self.__dict__ = load_json_object(file_name)
            else:
                raise IOError('The file {0} was not found.'.format(file_name))
        else:
            self.checking_entity = ''
            self.checking_level = '1'
            self.comments = ''
            self.contributors = ''
            self.license = 'CC BY-SA 4.0'
            self.publish_date = datetime.today().strftime('%Y-%m-%d')
            self.source_text = 'en'
            self.source_text_version = ''
            self.version = ''

    def to_serializable(self):
        return self.__dict__


def load_yaml_object(file_name, default=None):
    """
    Deserialized <file_name> into a Python object
    :param str|unicode file_name: The name of the file to read
    :param default: The value to return if the file is not found
    """
    if not os.path.isfile(file_name):
        return default

    # use utf-8-sig in case the file has a Byte Order Mark
    with codecs.open(file_name, 'r', 'utf-8-sig') as in_file:
        # read the text from the file
        content = in_file.read()

    # convert Windows line endings to Linux line endings
    content = content.replace('\r\n', '\n')

    # return a deserialized object
    return yaml.safe_load(content)


class TAMetaData(object):
    def __init__(self, file_name=None):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param str file_name: The name of a file to deserialize into a TAMetaData object
        """
        # deserialize
        if file_name:
            if os.path.isfile(file_name):
                meta = load_yaml_object(file_name)
                self.mod = int(time.time())
                self.manual = meta['manual']
                self.manual_title = meta['manual_title']
                self.volume = meta['volume']

                language = meta['language']
                self.language = {
                    'lc': language['code'],
                    'name': language['name'],
                    'anglicized_name': language['anglicized_name'],
                    'direction': language['direction']
                }

                self.status = TAStatus()
                self.status.checking_entity = meta['checking_entity']
                self.status.checking_level = meta['checking_level']
                self.status.comments = meta['comments']
                self.status.contributors = meta['contributors']
                self.status.license = meta['license']
                self.status.publish_date = meta['publish_date']
                self.status.source_text = meta['source_text']
                self.status.source_text_version = meta['source_text_version']
                self.status.version = meta['version']
            else:
                raise IOError('The file {0} was not found.'.format(file_name))
        else:
            self.mod = int(time.time())
            self.manual = ''
            self.manual_title = ''
            self.volume = ''

            self.language = {
                'lc': '',
                'name': '',
                'anglicized_name': '',
                'direction': 'ltr'
            }

            self.status = TAStatus()
            self.status.checking_entity = ''
            self.status.checking_level = ''
            self.status.comments = ''
            self.status.contributors = ''
            self.status.license = ''
            self.status.publish_date = ''
            self.status.source_text = ''
            self.status.source_text_version = ''
            self.status.version = ''

    def to_serializable(self):
        return self.__dict__


class TATableOfContents(object):
    def __init__(self, file_name=None):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param str file_name: The name of a file to deserialize into a TATableOfContents object
        """
        self.items = []  # type: list<TATableOfContentsItem>

        # deserialize
        if not file_name:
            return

        if not os.path.isfile(file_name):
            raise IOError('The file {0} was not found.'.format(file_name))

        toc = load_yaml_object(file_name)
        for item in toc:
            self.items.append(TATableOfContentsItem(item))

    def all_slugs(self):
        slugs = []

        for item in self.items:
            slugs = slugs + item.get_slugs()

        return slugs

    def to_markdown(self, manual_name):
        md = manual_name + '\n\n'

        for item in self.items:
            md += item.to_markdown(1)

        return md


class TATableOfContentsItem(object):
    starts_with_number_re = re.compile(r'^\d+\.\s', re.UNICODE)

    def __init__(self, initial_obj):
        self.title = initial_obj['title']
        self.slug = initial_obj['slug'] if 'slug' in initial_obj else ''
        self.sub_items = []  # type: list<TATableOfContentsItem>

        if 'subitems' not in initial_obj:
            return

        for item in initial_obj['subitems']:
            self.sub_items.append(TATableOfContentsItem(item))

    def __str__(self):
        return self.title

    def get_slugs(self):
        slugs = []
        if self.slug:
            slugs.append(self.slug)

        for item in self.sub_items:
            slugs = slugs + item.get_slugs()

        return slugs

    def to_markdown(self, level):

        indent = level - 1
        md = ('    ' * indent)

        prefix = ''
        if not TATableOfContentsItem.starts_with_number_re.match(self.title):
            prefix = '- '

        if self.slug:
            md += prefix + '[{0}]({1})'.format(self.title, self.slug)
        else:
            md += prefix + self.title

        md += '\n\n'

        if self.sub_items:
            for item in self.sub_items:
                md += item.to_markdown(level + 1)

        return md


class TAArticle(object):

    YAML_REGEX = re.compile(r'(---\s*\n)(.+?)(^-{3}\s*\n)+?(.*)$', re.DOTALL | re.MULTILINE)

    def __init__(self, content, slug):

        self.markdown = None  # type: str
        self.yaml = None      # type: str
        self.slug = slug

        match = TAArticle.YAML_REGEX.match(content)
        if match:
            self.yaml = self.get_yaml_data(match.group(2))

            if self.yaml:
                self.markdown = match.group(4)

    def __str__(self):
        if self.yaml:
            if 'title' in self.yaml:
                return self.yaml['title']

        if self.slug:
            return self.slug

        return 'TAArticle'

    def get_yaml_data(self, raw_yaml_text):

        return_val = {}

        # convert windows line endings
        cleaned = raw_yaml_text.replace('\r\n', '\n')

        # replace curly quotes
        cleaned = cleaned.replace('“', '"').replace('”', '"')

        # split into individual values, removing empty lines
        parts = filter(bool, cleaned.split('\n'))

        # check each value
        for part in parts:

            # split into name and value
            pieces = part.split(':', 1)

            # must be 2 pieces
            if len(pieces) != 2:
                print_error('Bad yaml format => ' + part)
                return None

            # try to parse
            # noinspection PyBroadException
            try:
                parsed = yaml.load(part)

            except:
                print_error('Not able to parse yaml value => ' + part)
                return None

            if not isinstance(parsed, dict):
                print_error('Yaml parse did not return the expected type => ' + part)
                return None

            # add the successfully parsed value to the dictionary
            for key in parsed.keys():
                return_val[key] = parsed[key]

        if not self.check_yaml_values(return_val):
            return None

        return return_val

    def check_yaml_values(self, yaml_data):

        return_val = True

        # check the required yaml values
        if not TAArticle.check_value_is_valid_int('volume', yaml_data):
            print_error('Volume value is not valid.')
            return_val = False

        if not self.check_value_is_valid_string('manual', yaml_data):
            print_error('Manual value is not valid.')
            return_val = False

        if not self.check_value_is_valid_string('slug', yaml_data):
            print_error('Volume value is not valid.')
            return_val = False
        else:
            # slug cannot contain a dash, only underscores
            test_slug = str(yaml_data['slug']).strip()
            if '-' in test_slug:
                print_error('Slug values cannot contain hyphen (dash).')
                return_val = False

        if not self.check_value_is_valid_string('title', yaml_data):
            print_error('Title value is not valid.')
            return_val = False

        return return_val

    def to_serializable(self):
        return_val = {
            'id': self.slug,
            'ref': 'vol{0}/{1}/{2}'.format(self.yaml['volume'], self.yaml['manual'], self.slug),
            'text': self.markdown,
            'title': self.yaml['title']
        }

        return return_val

    # noinspection PyBroadException
    @staticmethod
    def check_value_is_valid_int(value_to_check, yaml_data):

        if value_to_check not in yaml_data:
            print_error('"' + value_to_check + '" data value for page is missing')
            return False

        if not yaml_data[value_to_check]:
            print_error('"' + value_to_check + '" data value for page is blank')
            return False

        data_value = yaml_data[value_to_check]

        if not isinstance(data_value, int):
            try:
                data_value = int(data_value)
            except:
                try:
                    data_value = int(float(data_value))
                except:
                    return False

        return isinstance(data_value, int)

    @staticmethod
    def check_value_is_valid_string(value_to_check, yaml_data):

        if value_to_check not in yaml_data:
            print_error('"' + value_to_check + '" data value for page is missing')
            return False

        if not yaml_data[value_to_check]:
            print_error('"' + value_to_check + '" data value for page is blank')
            return False

        data_value = yaml_data[value_to_check]

        if not isinstance(data_value, str) and not isinstance(data_value, unicode):
            print_error('"' + value_to_check + '" data value for page is not a string')
            return False

        if not data_value.strip():
            print_error('"' + value_to_check + '" data value for page is blank')
            return False

        return True


class TAManual(object):

    def __init__(self, meta, toc):
        self.meta = meta    # type: TAMetaData
        self.toc = toc      # type: TATableOfContents
        self.articles = []  # type: list<TAArticle>

    def load_pages(self, content_dir):

        toc_slugs = self.toc.all_slugs()
        for slug in toc_slugs:

            print('Processing {0}...'.format(slug), end=' ')

            file_name = os.path.join(content_dir, slug + '.md')
            with codecs.open(file_name, 'r', 'utf-8-sig') as in_file:
                content = in_file.read()

            article = TAArticle(content, slug)
            if not article.yaml:
                print_error('No yaml data found for ' + slug)

            self.articles.append(article)

            print('finished.')

    def to_serializable(self):
        return_val = {
            'toc': self.toc.to_markdown(self.meta.manual_title),
            'meta': self.meta,
            'articles': []
        }

        for article in self.articles:
            return_val['articles'].append(article.to_serializable())
        return return_val
