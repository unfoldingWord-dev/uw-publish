#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#  Copyright (c) 2016 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Phil Hopper <phillip_hopper@wycliffeassociates.org>
#

from __future__ import print_function, unicode_literals
import argparse
import glob
import json
import os
import shutil
import sys
from general_tools.file_utils import make_dir, unzip, write_file
from general_tools.print_utils import print_notice, print_ok, print_error, print_warning
from general_tools.url_utils import join_url_parts, download_file
from app_code.ta.ta_classes import TAMetaData, TATableOfContents, TAManual, TAEncoder
from app_code.util.app_utils import get_output_dir

if sys.version_info < (3, 0):
    prompt = raw_input
else:
    prompt = input

# remember these so we can delete them
download_dir = ''


def main(git_repo):
    global download_dir

    # clean up the git repo url
    if git_repo[-4:] == '.git':
        git_repo = git_repo[:-4]

    if git_repo[-1:] == '/':
        git_repo = git_repo[:-1]

    # initialize some variables
    download_dir = '/tmp/{0}'.format(git_repo.rpartition('/')[2])
    make_dir(download_dir)
    downloaded_file = '{0}/{1}.zip'.format(download_dir, git_repo.rpartition('/')[2])
    file_to_download = join_url_parts(git_repo, 'archive/master.zip')
    metadata_obj = None
    content_dir = None
    toc_obj = None

    # download the repository
    try:
        print('Downloading {0}...'.format(file_to_download), end=' ')
        if not os.path.isfile(downloaded_file):
            download_file(file_to_download, downloaded_file)
    finally:
        print('finished.')

    try:
        print('Unzipping...'.format(downloaded_file), end=' ')
        unzip(downloaded_file, download_dir)
    finally:
        print('finished.')

    # examine the repository
    for root, dirs, files in os.walk(download_dir):

        if 'meta.yaml' in files:
            # read the metadata
            try:
                print('Reading the metadata...', end=' ')
                metadata_obj = TAMetaData(os.path.join(root, 'meta.yaml'))
            finally:
                print('finished.')

        if 'toc.yaml' in files:
            # read the table of contents
            try:
                print('Reading the toc...', end=' ')
                toc_obj = TATableOfContents(os.path.join(root, 'toc.yaml'))
            finally:
                print('finished.')

        if 'content' in dirs:
            content_dir = os.path.join(root, 'content')

        # if we have everything, exit the loop
        if content_dir and metadata_obj and toc_obj:
            break

    # check for valid repository structure
    if not metadata_obj:
        print_error('Did not find meta.yaml in {}'.format(git_repo))
        sys.exit(1)

    if not content_dir:
        print_error('Did not find the content directory in {}'.format(git_repo))
        sys.exit(1)

    if not toc_obj:
        print_error('Did not find toc.yaml in {}'.format(git_repo))
        sys.exit(1)

    # check for missing pages
    check_missing_pages(toc_obj, content_dir)

    # generate the pages
    print('Generating the manual...', end=' ')
    manual = TAManual(metadata_obj, toc_obj)
    manual.load_pages(content_dir)
    print('finished.')

    file_name = os.path.join(get_output_dir(), manual.meta.manual + '.json')
    print('saving to {0} ...'.format(file_name), end=' ')
    content = json.dumps(manual, sort_keys=True, indent=2, cls=TAEncoder)
    write_file(file_name, content)
    print('finished.')


def get_all_page_slugs(content_dir):

    slugs = []

    for f in glob.glob('{0}/*.md'.format(content_dir)):
        slugs.append(os.path.basename(f)[:-3])

    return slugs


def check_missing_pages(toc_obj, content_dir):

    toc_slugs = toc_obj.all_slugs()
    page_slugs = get_all_page_slugs(content_dir)
    not_in_pages = list(set(toc_slugs) - set(page_slugs))
    not_in_toc = list(set(page_slugs) - set(toc_slugs))

    if not_in_toc:
        print_warning('The following pages are in the content directory but not in the TOC:')
        for item in not_in_toc:
            print('- ' + item)
        print()
        print('If you continue these pages will NOT be included in the published product.')
        print()
        resp = prompt('Do you want to continue with the data as it is? [Y|n]: ')
        if resp != '' and resp[0:1].lower() != 'y':
            sys.exit(0)

    if not_in_pages:
        print_error('The following pages are in the TOC but were not found in the content directory:')
        for item in not_in_pages:
            print('- ' + item)
        print()
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r', '--gitrepo', dest='gitrepo', default=False,
                        required=True, help='Git repository where the source can be found.')

    args = parser.parse_args(sys.argv[1:])

    # prompt user to update meta.json
    print_notice('Check meta.yaml in the git repository and update the information if needed.')
    prompt('Press Enter to continue when ready...')

    try:
        print_ok('STARTING: ', 'publishing TA repository.')
        main(args.gitrepo)
        print_ok('ALL FINISHED: ', 'publishing TA repository.')
        print_notice('Don\'t forget to notify the interested parties.')

    finally:
        # delete temp files
        if os.path.isdir(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
