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
import codecs
import os
import shutil
import subprocess
import sys
from uw.update_catalog import update_catalog
from app_code.cli.obs_in_progress import ObsInProgress
from app_code.obs.obs_classes import OBSStatus, OBS
from general_tools.file_utils import make_dir
from general_tools.print_utils import print_warning, print_error, print_notice, print_ok
from general_tools.url_utils import download_file, get_languages, join_url_parts

if sys.version_info < (3, 0):
    prompt = raw_input
else:
    prompt = input

# remember these so we can delete them
download_dir = ''

root = '/var/www/vhosts/door43.org/httpdocs/data/gitrepo/pages/{0}/obs/{1}'
api_dir = '/var/www/vhosts/api.unfoldingword.org/httpdocs/obs/txt/1/{0}'


def import_obs(lang_data, git_repo, door43_url, no_pdf):
    global download_dir, root, api_dir

    lang_code = lang_data['lc']

    # pre-flight checklist
    link_source = '/var/www/vhosts/api.unfoldingword.org/httpdocs/obs/jpg/1/en'
    if not os.path.isdir(link_source):
        print_error('Image source directory not found: {0}.'.format(link_source))
        sys.exit(1)

    if git_repo[-1:] != '/':
        git_repo += '/'

    if no_pdf:
        tools_dir = None
    else:
        tools_dir = '/var/www/vhosts/door43.org/tools'
        if not os.path.isdir(tools_dir):
            tools_dir = os.path.expanduser('~/Projects/tools')

        # prompt if tools not found
        if not os.path.isdir(tools_dir):
            tools_dir = None
            print_notice('The tools directory was not found. The PDF cannot be generated.')
            resp = prompt('Do you want to continue without generating a PDF? [Y|n]: ')
            if resp != '' and resp != 'Y' and resp != 'y':
                sys.exit(0)

    if git_repo:
        if git_repo[-1:] == '/':
            git_repo = git_repo[:-1]

        download_dir = '/tmp/{0}'.format(git_repo.rpartition('/')[2])
        make_dir(download_dir)

        # make sure OBS is initialized on Dokuwiki
        test_dir = root.format(lang_code, '')
        if not os.path.isdir(test_dir):
            print_warning('It seems OBS has not been initialized on Door43.org for {0}'.format(lang_code))
            sys.exit(1)

    elif door43_url:
        print_error('URL not yet implemented.')
        return
    else:
        print_error('Source not provided.')
        return

    # get the source files from the git repository
    if 'github' in git_repo:
        # https://github.com/unfoldingWord/obs-ru
        # https://raw.githubusercontent.com/unfoldingWord/obs-ru/master/obs-ru.json
        raw_url = git_repo.replace('github.com', 'raw.githubusercontent.com')
    elif 'git.door43.org' in git_repo:
        raw_url = join_url_parts(git_repo, 'raw')
    else:
        # this is to keep IntelliJ happy, is should have been caught in sub main
        return

    # download needed files from the repository
    file_suffix = '-{0}.json'.format(lang_code.lower())
    files_to_download = [
        join_url_parts(raw_url, 'master/obs' + file_suffix),
        join_url_parts(raw_url, 'master/status' + file_suffix)
    ]

    for file_to_download in files_to_download:

        downloaded_file = os.path.join(download_dir, file_to_download.rpartition('/')[2])

        try:
            print('Downloading {0}...'.format(file_to_download), end=' ')
            download_file(file_to_download, downloaded_file)
        finally:
            print('finished.')

    # read the files from the git repository
    file_suffix = '-{0}.json'.format(lang_code.lower())
    obs_obj = None
    status_obj = None
    # front_matter_found = False
    # back_matter_found = False

    try:
        print('Examining the files...', end=' ')
        for root_path, dirs, files in os.walk(download_dir):

            if not len(files):
                continue

            for git_file in files:
                if git_file == 'obs' + file_suffix:
                    obs_obj = OBS(os.path.join(root_path, git_file))
                elif git_file == 'status' + file_suffix:
                    status_obj = OBSStatus(os.path.join(root_path, git_file))
                    # elif 'front-matter' in git_file:
                    #     front_matter_found = True
                    # elif 'back-matter' in git_file:
                    #     back_matter_found = True
    finally:
        print('finished.')

    # check data integrity
    if not obs_obj.verify_all():
        sys.exit(1)

    if not status_obj:
        print_error('The file "status{0}" was not found in the git repository.'.format(file_suffix))
        sys.exit(1)

    # create Dokuwiki pages
    print_notice('Begin creating Dokuwiki pages.')
    for chapter in obs_obj.chapters:

        chapter_title = '====== {0} ======'.format(chapter['title'])
        chapter_ref = '//{0}//'.format(chapter['ref'])
        chapter_body = ''
        chapter_num = chapter['number'].zfill(2)

        for frame in chapter['frames']:
            chapter_body += '{{{{{0}?direct&}}}}\n\n{1}\n\n'.format(frame['img'], frame['text'])

        file_name = root.format(lang_code, chapter_num + '.txt')
        print('  Writing {0}'.format(file_name))
        with codecs.open(file_name, 'w', 'utf-8-sig') as out_file:
            out_file.write('{0}\n\n{1}{2}\n'.format(chapter_title, chapter_body, chapter_ref))

    print_notice('Finished creating Dokuwiki pages.')

    # Create image symlinks on api.unfoldingword.org
    try:
        print('Creating symlink to images directory...', end=' ')
        link_name = '/var/www/vhosts/api.unfoldingword.org/httpdocs/obs/jpg/1/{0}'.format(lang_code.lower())
        if not os.path.isfile(link_name) and not os.path.islink(link_name):
            os.symlink(link_source, link_name)
    finally:
        print('finished.')

    # Create PDF via ConTeXt
    if not no_pdf and tools_dir and os.path.isdir(tools_dir):
        try:
            print_notice('Beginning PDF generation.')
            script_file = os.path.join(tools_dir, 'obs/book/pdf_export.sh')
            out_dir = api_dir.format(lang_code)
            make_dir(out_dir)
            process = subprocess.Popen([script_file,
                                        '-l', lang_code,
                                        '-c', status_obj.checking_level,
                                        '-v', status_obj.version,
                                        '-o', out_dir],
                                       shell=True,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

            # wait for the process to terminate
            out, err = process.communicate()
            exit_code = process.returncode
            out = out.strip().decode('utf-8')
            err = err.strip().decode('utf-8')

            # the error message may be in stdout
            if exit_code != 0:
                if not err:
                    err = out
                    out = None

            if err:
                print_error(err, 2)

            if out:
                print('  ' + out)

            print('  PDF subprocess finished with exit code {0}'.format(exit_code))

        finally:
            print_notice('Finished generating PDF.')


if __name__ == '__main__':
    print()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-l', '--lang', dest='lang', default=False,
                        required=True, help='Language code of resource.')
    parser.add_argument('-r', '--gitrepo', dest='gitrepo', default=False,
                        required=False, help='Git repository where the source can be found.')
    parser.add_argument('-u', '--url', dest='url', default=False,
                        required=False, help='Door43 page where the source can be found.')
    parser.add_argument('-p', '--nopdf', dest='nopdf', action='store_true', help='Do not produce a PDF.')

    args = parser.parse_args(sys.argv[1:])

    if not args.gitrepo and not args.url:
        print_error('You must provide either --gitrepo or --url to this script.')
        sys.exit(0)

    try:
        # get the language data
        try:
            print('Downloading language data...', end=' ')
            langs = get_languages()
        finally:
            print('finished.')

        this_lang = next(l for l in langs if l['lc'] == args.lang)

        if not this_lang:
            print_error('Information for language "{0}" was not found.'.format(args.lang))
            sys.exit(1)

        if 'github' not in args.gitrepo and 'git.door43.org' not in args.gitrepo:
            print_warning('Currently only github and git.door43.org repositories are supported.')
            sys.exit(0)

        # prompt user to update status.txt
        print_notice(
            'Check status-{0}.json in the git repository and update the information if needed.'.format(args.lang))
        prompt('Press Enter to continue when ready...')
        print()

        # do the import
        import_obs(this_lang, args.gitrepo, args.url, args.nopdf)

        # update the catalog
        print_ok('STARTING: ', 'updating the catalogs.')
        update_catalog()
        print_ok('FINISHED: ', 'updating the catalogs.')

        # update OBS in-progress
        print_ok('STARTING: ', 'updating OBS in progress.')
        ObsInProgress.run()
        print_ok('FINISHED: ', 'updating OBS in progress.')

        print_ok('FINISHED: ', 'Please check door43.org and api.unfoldingword.org.')
        print_notice('Don\'t forget to notify the interested parties.')

    finally:
        # delete temp files
        if os.path.isdir(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
