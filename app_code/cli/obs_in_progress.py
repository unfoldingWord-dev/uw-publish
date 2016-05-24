#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#  Copyright (c) 2014, 2016 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Jesse Griffin <jesse@distantshores.org>
#  Phil Hopper <phillip_hopper@wycliffeassociates.org>
#

"""
Writes a JSON catalog of in progress OBS translations based on door43.org.
"""

from __future__ import print_function, unicode_literals
import json
import shlex
import datetime
from subprocess import *
from general_tools.file_utils import write_file
from general_tools.url_utils import get_url


class ObsInProgress(object):

    pages = '/var/www/vhosts/door43.org/httpdocs/data/gitrepo/pages'
    lang_names = 'http://td.unfoldingword.org/exports/langnames.json'
    obs_cat = 'https://api.unfoldingword.org/obs/txt/1/obs-catalog.json'
    obs_in_progress_file_name = '/var/www/vhosts/api.unfoldingword.org/httpdocs/obs/txt/1/obs-in-progress.json'

    @staticmethod
    def run():
        cat = json.loads(get_url(ObsInProgress.lang_names))
        pub_cat = json.loads(get_url(ObsInProgress.obs_cat))
        ObsInProgress.main(cat, pub_cat)

    @staticmethod
    def shell_command(c):
        """
        Runs a command in a shell.  Returns output and return code of command.
        :param str|unicode c: The command to run
        :return: str, int
        """
        command = shlex.split(c)
        com = Popen(command, shell=False, stdout=PIPE, stderr=PIPE)
        stdout = ''.join(com.communicate()).strip()
        return stdout, com.returncode

    @staticmethod
    def main(catalog, published_catalog):

        # get a list of the language codes already completed/published
        pub_list = [x['language'] for x in published_catalog]

        # get a list of the languages for which OBS has been initialized
        out, ret = ObsInProgress.shell_command('find {0} -maxdepth 2 -type d -name obs'.format(ObsInProgress.pages))

        # start building the in-progress list
        in_progress_languages = []
        for line in out.split('\n'):

            # get the language code from the OBS namespace
            lc = line.split('/')[9]

            # skip this language if it is in the list of published languages
            if lc in pub_list:
                continue

            # make sure the language is in the official list of languages
            for x in catalog:
                if lc == x['lc']:
                    in_progress_languages.append({'lc': lc, 'ln': x['ln']})
                    break

        # now that we have the list of in-progress languages, sort it by language code
        in_progress_languages.sort(key=lambda item: item['lc'])

        # add a date-stamp
        today = ''.join(str(datetime.date.today()).rsplit('-')[0:3])
        in_progress_languages.append({'date_modified': today})

        # save the results to a file
        write_file(ObsInProgress.obs_in_progress_file_name, in_progress_languages)


if __name__ == '__main__':
    ObsInProgress.run()
