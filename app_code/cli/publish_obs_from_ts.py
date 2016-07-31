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
import glob
import json
import shutil
import datetime
import subprocess
from general_tools.file_utils import make_dir, unzip, load_json_object, write_file
from general_tools.git_wrapper import *
from general_tools.print_utils import print_error, print_ok, print_notice
from general_tools.url_utils import join_url_parts, download_file
from app_code.cli.obs_published_langs import ObsPublishedLangs
from app_code.obs.export_to_tex import OBSTexExport
from app_code.obs.obs_classes import OBSStatus, OBS, OBSChapter, OBSEncoder
from uw.update_catalog import update_catalog
import sys
import os

if sys.version_info < (3, 0):
    prompt = raw_input
else:
    prompt = input

# remember this so we can delete it
download_dir = ''

door43_root = '/var/www/vhosts/door43.org/httpdocs/data/gitrepo'
pages = os.path.join(door43_root, 'pages')
uwadmin_dir = os.path.join(pages, 'en/uwadmin')
unfoldingWord_dir = '/var/www/vhosts/api.unfoldingword.org/httpdocs/obs/txt/1/'
lang_cat = None
github_org = None


def main(git_repo, tag, no_pdf):
    global download_dir

    # clean up the git repo url
    if git_repo[-4:] == '.git':
        git_repo = git_repo[:-4]

    if git_repo[-1:] == '/':
        git_repo = git_repo[:-1]

    # initialize some variables
    today = ''.join(str(datetime.date.today()).rsplit('-')[0:3])  # str(datetime.date.today())
    download_dir = '/tmp/{0}'.format(git_repo.rpartition('/')[2])
    make_dir(download_dir)
    downloaded_file = '{0}/{1}.zip'.format(download_dir, git_repo.rpartition('/')[2])
    file_to_download = join_url_parts(git_repo, 'archive/' + tag + '.zip')
    manifest = None
    status = None  # type: OBSStatus
    content_dir = None

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

        if 'manifest.json' in files:
            # read the manifest
            try:
                print('Reading the manifest...', end=' ')
                content_dir = root
                manifest = load_json_object(os.path.join(root, 'manifest.json'))
            finally:
                print('finished.')

        if 'status.json' in files:
            # read the meta data
            try:
                print('Reading the status...', end=' ')
                content_dir = root
                status = OBSStatus(os.path.join(root, 'status.json'))
            finally:
                print('finished.')

        # if we have everything, exit the loop
        if content_dir and manifest and status:
            break

    # check for valid repository structure
    if not manifest:
        print_error('Did not find manifest.json in {}'.format(git_repo))
        sys.exit(1)

    if not status:
        print_error('Did not find status.json in {}'.format(git_repo))
        sys.exit(1)

    print('Initializing OBS object...', end=' ')
    lang = manifest['target_language']['id']
    obs_obj = OBS()
    obs_obj.date_modified = today
    obs_obj.direction = manifest['target_language']['direction']
    obs_obj.language = lang
    print('finished')

    obs_obj.chapters = load_obs_chapters(content_dir)
    obs_obj.chapters.sort(key=lambda c: c['number'])

    if not obs_obj.verify_all():
        print_error('Quality check did not pass.')
        sys.exit(1)

    print('Loading languages...', end=' ')
    lang_dict = OBS.load_lang_strings()
    print('finished.')

    print('Loading the catalog...', end=' ')
    export_dir = '/var/www/vhosts/door43.org/httpdocs/exports'
    # uw_cat_path = os.path.join(unfoldingWord_dir, 'obs-catalog.json')
    # uw_catalog = load_json_object(uw_cat_path, [])
    # uw_cat_langs = [x['language'] for x in uw_catalog]
    cat_path = os.path.join(export_dir, 'obs-catalog.json')
    catalog = load_json_object(cat_path, [])
    print('finished')

    print('Getting already published languages...', end=' ')
    json_lang_file_path = os.path.join(export_dir, lang, 'obs', 'obs-{0}.json'.format(lang))
    # prev_json_lang = load_json_object(json_lang_file_path, {})

    if lang not in lang_dict:
        print("Configuration for language {0} missing.".format(lang))
        sys.exit(1)
    print('finished.')

    updated = update_language_catalog(lang, obs_obj.direction, status, today, lang_dict, catalog)

    print('Writing the OBS file to the exports directory...', end=' ')
    cur_json = json.dumps(obs_obj, sort_keys=True, cls=OBSEncoder)

    if updated:
        ([x for x in catalog if x['language'] == lang][0]['date_modified']) = today
        write_file(json_lang_file_path.replace('.txt', '.json'), cur_json)
    print('finished.')

    export_to_api(lang, status, today, cur_json)

    cat_json = json.dumps(catalog, sort_keys=True, cls=OBSEncoder)
    write_file(cat_path, cat_json)

    # update the catalog
    print_ok('STARTING: ', 'updating the catalogs.')
    update_catalog()
    print_ok('FINISHED: ', 'updating the catalogs.')

    if no_pdf:
        return

    create_pdf(lang, status.checking_level, status.version)


def create_pdf(lang_code, checking_level, version):
    global download_dir, unfoldingWord_dir

    # Create PDF via ConTeXt
    try:
        print_ok('BEGINNING: ', 'PDF generation.')
        out_dir = os.path.join(download_dir, 'make_pdf')
        make_dir(out_dir)

        # generate a tex file
        print('Generating tex file...', end=' ')
        tex_file = os.path.join(out_dir, '{0}.tex'.format(lang_code))

        # make sure it doesn't already exist
        if os.path.isfile(tex_file):
            os.remove(tex_file)

        with OBSTexExport(lang_code, tex_file, 0, '360px', checking_level) as tex:
            tex.run()
        print('finished.')

        # run context
        print_notice('Running context - this may take several minutes.')

        trackers = ','.join(['afm.loading', 'fonts.missing', 'fonts.warnings', 'fonts.names',
                             'fonts.specifications', 'fonts.scaling', 'system.dump'])

        cmd = 'context --paranoid --batchmode --trackers={0} "{1}"'.format(trackers, tex_file)

        try:
            subprocess.check_call(cmd, shell=True, stderr=subprocess.STDOUT, cwd=out_dir)

        except subprocess.CalledProcessError as e:
            if e.message:
                raise e
        print('Finished running context.')

        print('Copying PDF to API...', end=' ')
        version = version.replace('.', '_')
        if version[0:1] != 'v':
            version = 'v' + version

        pdf_file = os.path.join(unfoldingWord_dir, lang_code, 'obs-{0}-{1}.pdf'.format(lang_code, version))
        shutil.copyfile(os.path.join(out_dir, '{0}.pdf'.format(lang_code)), pdf_file)
        print('finished.')

    finally:
        print_ok('FINISHED:', 'generating PDF.')


def export_to_api(lang, status, today, cur_json):
    global unfoldingWord_dir, lang_cat, github_org, pages

    print('Getting Github credentials...', end=' ')
    try:
        github_org = None
        if os.path.isfile('/root/.github_pass'):
            pw = open('/root/.github_pass', 'r').read().strip()
            g_user = githubLogin('dsm-git', pw)
            github_org = getGithubOrg('unfoldingword', g_user)
        else:
            print('none found...', end=' ')
    except GithubException as e:
        print_error('Problem logging into Github: {0}'.format(e))
        sys.exit(1)
    print('finished.')

    print('Loading the uw catalog...', end=' ')
    uw_cat_path = os.path.join(unfoldingWord_dir, 'obs-catalog.json')
    uw_catalog = load_json_object(uw_cat_path, [])
    uw_cat_langs = [x['language'] for x in uw_catalog]
    print('finished')

    unfolding_word_lang_dir = os.path.join(unfoldingWord_dir, lang)
    if 'checking_level' in status and 'publish_date' in status:
        if status.checking_level in ['1', '2', '3']:

            front_json = OBS.get_front_matter(pages, lang, today)
            back_json = OBS.get_back_matter(pages, lang, today)

            print('Exporting {0}...'.format(lang), end=' ')
            export_unfolding_word(status, unfolding_word_lang_dir, cur_json,
                                  lang, github_org, front_json, back_json)
            if lang in uw_cat_langs:
                uw_catalog.pop(uw_cat_langs.index(lang))
                uw_cat_langs.pop(uw_cat_langs.index(lang))
            uw_catalog.append(lang_cat)

            uw_cat_json = json.dumps(uw_catalog, sort_keys=True, cls=OBSEncoder)
            write_file(uw_cat_path, uw_cat_json)

            # update uw_admin status page
            ObsPublishedLangs.update_page(ObsPublishedLangs.cat_url, ObsPublishedLangs.uw_stat_page)

            print('finished.')
        else:
            print_error('The `checking_level` is invalid.')
            sys.exit(1)
    else:
        print_error('The status is missing `checking_level` or `publish_date`.')
        sys.exit(1)


def export_unfolding_word(status, git_dir, json_data, lang_code, github_organization, front_matter, back_matter):
    """
    Exports JSON data for each language into its own Github repo.
    """
    global github_org
    write_file(os.path.join(git_dir, 'obs-{0}.json'.format(lang_code)), json_data)
    write_file(os.path.join(git_dir, 'obs-{0}-front-matter.json'.format(lang_code)), front_matter)
    write_file(os.path.join(git_dir, 'obs-{0}-back-matter.json'.format(lang_code)), back_matter)
    status_str = json.dumps(status, sort_keys=True, cls=OBSEncoder)
    write_file(os.path.join(git_dir, 'status-{0}.json'.format(lang_code)), status_str)
    write_file(os.path.join(git_dir, 'README.md'), OBS.get_readme_text())

    if not github_org:
        return

    gitCreate(git_dir)
    name = 'obs-{0}'.format(lang_code)
    desc = 'Open Bible Stories for {0}'.format(lang_code)
    url = 'http://unfoldingword.org/{0}/'.format(lang_code)
    githubCreate(git_dir, name, desc, url, github_organization)
    commit_msg = status_str
    gitCommit(git_dir, commit_msg)
    gitPush(git_dir)


def update_language_catalog(lang, direction, status, date_modified, lang_dict, catalog):
    global lang_cat

    print('Updating the language catalog...', end=' ')
    lang_cat = {'language': lang,
                'string': lang_dict[lang],
                'direction': direction,
                'date_modified': date_modified,
                'status': status,
                }

    updated = False

    if lang not in [x['language'] for x in catalog]:
        catalog.append(lang_cat)
        updated = True
    else:
        for i in range(0, len(catalog)):
            if catalog[i]['language'] == lang:
                catalog[i] = lang_cat
                updated = True
    print('finished.')

    return updated


def load_obs_chapters(content_dir):
    print('Reading OBS pages...', end=' ')
    chapters = []
    img_url = 'https://cdn.door43.org/obs/jpg/360px/obs-en-{0}.jpg'
    for story_num in range(1, 51):
        chapter_num = str(story_num).zfill(2)
        story_dir = os.path.join(content_dir, chapter_num)
        obs_chapter = OBSChapter()
        obs_chapter.number = chapter_num

        # get the translated chapter ref
        with codecs.open(os.path.join(story_dir, 'reference.txt'), 'r', encoding='utf-8-sig') as in_file:
            obs_chapter.ref = in_file.read()

        # get the translated chapter title
        with codecs.open(os.path.join(story_dir, 'title.txt'), 'r', encoding='utf-8-sig') as in_file:
            obs_chapter.title = in_file.read()

        # loop through the frames for this chapter
        frame_list = glob.glob('{0}/[0-9][0-9].txt'.format(story_dir))
        for frame_file in frame_list:
            with codecs.open(frame_file, 'r', encoding='utf-8-sig') as in_file:
                frame_text = in_file.read()

            frame_id = chapter_num + '-' + os.path.splitext(os.path.basename(frame_file))[0]

            frame = {'id': frame_id,
                     'img': img_url.format(frame_id),
                     'text': frame_text
                     }

            obs_chapter.frames.append(frame)

        # sort the frames by id
        obs_chapter.frames.sort(key=lambda f: f['id'])

        # add this chapter to the OBS object
        chapters.append(obs_chapter)

    print('finished.')
    return chapters


if __name__ == '__main__':
    print()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r', '--gitrepo', dest='gitrepo', default=False,
                        required=True, help='Git repository where the source can be found.')
    parser.add_argument('-t', '--tag', dest='tag', default='master',
                        required=False, help='Branch or tag to use as the source. Default is master.')
    parser.add_argument('-p', '--nopdf', dest='nopdf', action='store_true', help='Do not produce a PDF.')

    args = parser.parse_args(sys.argv[1:])

    # prompt user to update status.json
    print_notice('Check status.json in the git repository and update the information if needed.')
    prompt('Press Enter to continue when ready...')

    try:
        print_ok('STARTING: ', 'publishing OBS repository.')
        main(args.gitrepo, args.tag, args.nopdf)
        print_ok('ALL FINISHED: ', 'publishing OBS repository.')
        print_notice('Don\'t forget to notify the interested parties.')

    finally:
        # delete temp files
        if os.path.isdir(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
