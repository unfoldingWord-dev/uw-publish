from __future__ import print_function, unicode_literals
import codecs
from datetime import datetime
import os
from json import JSONEncoder

import chapters_and_frames
from general_tools.file_utils import load_json_object
from app_code.util import app_utils


class OBSStatus(object):
    def __init__(self, file_name=None):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param str file_name: The name of a file to deserialize into a OBSStatus object
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
            self.publish_date = datetime.today().strftime('%Y-%m-%d')
            self.source_text = 'en'
            self.source_text_version = ''
            self.version = ''


class OBSChapter(object):
    def __init__(self, json_obj=None):
        """
        Class constructor. Optionally accepts an object for initialization.
        :param object json_obj: The name of a file to deserialize into a OBSStatus object
        """
        # deserialize
        if json_obj:
            self.__dict__ = json_obj  # type: dict

        else:
            self.frames = []
            self.number = ''
            self.ref = ''
            self.title = ''

    def get_errors(self):
        """
        Checks this chapter for errors
        :returns list<str>
        """
        errors = []

        if not self.title:
            msg = 'Title not found: {0}'.format(self.number)
            print(msg)
            errors.append(msg)

        if not self.ref:
            msg = 'Ref not found: {0}'.format(self.number)
            print(msg)
            errors.append(msg)

        chapter_index = int(self.number) - 1

        # get the expected number of frames for this chapter
        expected_frame_count = chapters_and_frames.frame_counts[chapter_index]

        for x in range(1, expected_frame_count + 1):

            # frame id is formatted like '01-01'
            frame_id = self.number.zfill(2) + '-' + str(x).zfill(2)

            # get the next frame
            frame = next((f for f in self.frames if f['id'] == frame_id), None)
            if not frame:
                msg = 'Frame not found: {0}'.format(frame_id)
                print(msg)
                errors.append(msg)
            else:
                # check the frame img and  values
                if 'img' not in frame or not frame['img']:
                    msg = 'Attribute "img" is missing for frame {0}'.format(frame_id)
                    print(msg)
                    errors.append(msg)

                if 'text' not in frame or not frame['text']:
                    msg = 'Attribute "text" is missing for frame {0}'.format(frame_id)
                    print(msg)
                    errors.append(msg)

        return errors

    def __getitem__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

    def __str__(self):
        return self.__class__.__name__ + ' ' + self.number


class OBS(object):
    def __init__(self, file_name=None):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param str file_name: The name of a file to deserialize into a OBS object
        """
        # deserialize
        if file_name:
            if os.path.isfile(file_name):
                self.__dict__ = load_json_object(file_name)
            else:
                raise IOError('The file {0} was not found.'.format(file_name))
        else:
            self.app_words = dict(cancel='Cancel',
                                  chapters='Chapters',
                                  languages='Languages',
                                  next_chapter='Next Chapter',
                                  ok='OK',
                                  remove_locally='Remove Locally',
                                  remove_this_string='Remove this language from offline storage. You will need an '
                                                     'internet connection to view it in the future.',
                                  save_locally='Save Locally',
                                  save_this_string='Save this language locally for offline use.',
                                  select_a_language='Select a Language')
            self.chapters = []
            self.date_modified = datetime.today().strftime('%Y%m%d')
            self.direction = 'ltr'
            self.language = ''

    def verify_all(self):

        errors = []

        for chapter in self.chapters:
            obs_chapter = OBSChapter(chapter)
            errors = errors + obs_chapter.get_errors()

        if len(errors) == 0:
            print('No errors were found in the OBS data.')
            return True
        else:
            return False

    @staticmethod
    def load_static_json_file(file_name):
        file_name = os.path.join(app_utils.get_static_dir(), file_name)
        return load_json_object(file_name, {})

    @staticmethod
    def get_readme_text():
        file_name = os.path.join(app_utils.get_static_dir(), 'obs_readme.md')
        with codecs.open(file_name, 'r', encoding='utf-8') as in_file:
            return in_file.read()

    @staticmethod
    def get_front_matter():
        return OBS.load_static_json_file('obs-front-matter.json')

    @staticmethod
    def get_back_matter():
        return OBS.load_static_json_file('obs-back-matter.json')

    @staticmethod
    def get_status():
        return OBS.load_static_json_file('obs-status.json')


class OBSEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
