from __future__ import unicode_literals
import os
from datetime import datetime
from general_tools.file_utils import load_json_object


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
