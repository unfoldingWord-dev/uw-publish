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

from __future__ import print_function, unicode_literals
import sys
import json
import codecs
from general_tools.url_utils import get_url


class ObsPublishedLangs(object):
    cat_url = 'https://api.unfoldingword.org/obs/txt/1/obs-catalog.json'
    uw_stat_page = '/var/www/vhosts/door43.org/httpdocs/data/gitrepo/pages/en/uwadmin/pub_status.txt'
    pub_status_template = '====== unfoldingWord OBS Published Languages ======\n'
    lang_template = '''
    ===== {0} =====
    ^Language   ^Publish Date   ^Version    ^Checking Level ^
    |  [[:en:uwadmin:{0}:obs:status|{1}]]  |  {2}  |  {3}  |  {{{{https://api.unfoldingword.org/obs/jpg/1/checkinglevels/uW-Level{4}-32px.png}}}}  |
    '''

    @staticmethod
    def get_cat(url):
        """
        Get's latest catalog from server.
        """
        # noinspection PyBroadException
        try:
            response = get_url(url)
        except:
            print("  => ERROR retrieving %s\nCheck the URL" % url)
            sys.exit(1)
        return json.loads(response)

    @staticmethod
    def update_uw_status(cat, fd):
        for e in cat:
            fd.write(ObsPublishedLangs.lang_template.format(e['language'],
                                                            e['string'],
                                                            e['status']['publish_date'],
                                                            e['status']['version'],
                                                            e['status']['checking_level']))

    @staticmethod
    def update_page(cat_url, uw_stat_page):
        cat = ObsPublishedLangs.get_cat(cat_url)
        with codecs.open(uw_stat_page, 'w', encoding='utf-8') as out_file:
            out_file.write(ObsPublishedLangs.pub_status_template)
            ObsPublishedLangs.update_uw_status(cat, out_file)


if __name__ == '__main__':
    ObsPublishedLangs.update_page(ObsPublishedLangs.cat_url, ObsPublishedLangs.uw_stat_page)
