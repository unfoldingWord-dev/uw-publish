from __future__ import print_function, unicode_literals
from datetime import datetime
import os
import chapters_and_frames
from general_tools.file_utils import load_json_object


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
            self.__dict__ = json_obj

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
