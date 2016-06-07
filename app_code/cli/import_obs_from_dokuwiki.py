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
#  Requires PyGithub for unfoldingWord export.

from __future__ import print_function, unicode_literals
import codecs
import json
import re
import glob
import argparse
import datetime
from general_tools.git_wrapper import *
from general_tools.file_utils import write_file, load_json_object
from general_tools.smartquotes import smartquotes
from app_code.cli.obs_published_langs import ObsPublishedLangs
from app_code.obs.obs_classes import OBS, OBSChapter, OBSEncoder
from app_code.util.languages import Language
import os
import sys

root = '/var/www/vhosts/door43.org/httpdocs/data/gitrepo'
pages = os.path.join(root, 'pages')
uwadmin_dir = os.path.join(pages, 'en/uwadmin')
export_dir = '/var/www/vhosts/door43.org/httpdocs/exports'
unfoldingWord_dir = '/var/www/vhosts/api.unfoldingword.org/httpdocs/obs/txt/1/'
rtl = ['he', 'ar', 'fa']
img_url = 'https://api.unfoldingword.org/obs/jpg/1/{0}/360px/obs-{0}-{1}.jpg'


status_headers = ('publish_date',
                  'version',
                  'contributors',
                  'checking_entity',
                  'checking_level',
                  'source_text',
                  'source_text_version',
                  'comments'
                  )

# regular expressions for splitting the chapter into components
title_re = re.compile(r'======.*', re.UNICODE)
ref_re = re.compile(r'//.*//', re.UNICODE)
frame_re = re.compile(r'{{[^{]*', re.DOTALL | re.UNICODE)
fr_id_re = re.compile(r'[0-5][0-9]-[0-9][0-9]', re.UNICODE)
num_re = re.compile(r'([0-5][0-9]).txt', re.UNICODE)

# regular expressions for removing text formatting
html_tag_re = re.compile(r'<.*?>', re.UNICODE)
link_tag_re = re.compile(r'\[\[.*?\]\]', re.UNICODE)
img_tag_re = re.compile(r'{{.*?}}', re.UNICODE)
img_link_re = re.compile(r'https://.*\.(jpg|jpeg|gif)', re.UNICODE)

# regular expressions for front matter
obs_name_re = re.compile(r'\| (.*)\*\*', re.UNICODE)
tag_line_re = re.compile(r'\n\*\*.*openbiblestories', re.UNICODE | re.DOTALL)
link_re = re.compile(r'\[\[.*?\]\]', re.UNICODE)


def get_chapter(chapter_path, chapter_number):

    with codecs.open(chapter_path, 'r', encoding='utf-8') as in_file:
        chapter = in_file.read()

    obs_chapter = OBSChapter()
    obs_chapter.number = chapter_number

    # Get title for chapter
    title = title_re.search(chapter)
    if title:
        obs_chapter.title = title.group(0).replace('=', '').strip()

    # Get reference for chapter
    ref = ref_re.search(chapter)
    if ref:
        obs_chapter.ref = ref.group(0).replace('/', '').strip()

    # Get the frames
    for fr in frame_re.findall(chapter):
        fr_lines = fr.split('\n')
        fr_se = fr_id_re.search(fr)
        if not fr_se:
            continue

        fr_id = fr_se.group(0)
        frame = {'id': fr_id,
                 'img': get_img(fr_lines[0].strip(), fr_id),
                 'text': get_text(fr_lines[1:])
                 }
        obs_chapter.frames.append(frame)

    # Sort frames
    obs_chapter.frames.sort(key=lambda f: f['id'])
    return obs_chapter


def get_img(link, frame_id):
    link_se = img_link_re.search(link)
    if link_se:
        link = link_se.group(0)
        return link
    return img_url.format('en', frame_id)


def get_text(lines):
    """
    Groups lines into a string and runs through cleanText and smartquotes.
    """
    text = ''.join([y for y in lines[1:] if '//' not in y]).strip()
    text = text.replace('\\\\', '').replace('**', '').replace('__', '')
    text = clean_text(text)
    text = smartquotes(text)
    return text


def clean_text(text):
    """
    Cleans up text from possible DokuWiki and HTML tag pollution.
    """
    if html_tag_re.search(text):
        text = html_tag_re.sub('', text)
    if link_tag_re.search(text):
        text = link_tag_re.sub('', text)
    if img_tag_re.search(text):
        text = img_tag_re.sub('', text)
    return text


def write_page(outfile, p):
    write_file(outfile.replace('.txt', '.json'), p)


def get_dump(j):
    return json.dumps(j, sort_keys=True)


def load_lang_strings():
    langs = Language.load_languages()
    return_val = {}
    if not langs:
        return return_val

    for lang_obj in langs:  # :type Language
        return_val[lang_obj.lc] = lang_obj.ln

    return return_val


def get_json_dict(stat_file):
    return_val = {}
    if os.path.isfile(stat_file):
        for line in codecs.open(stat_file, 'r', encoding='utf-8'):

            if line.startswith('#') or line.startswith('\n') or line.startswith('{{') or ':' not in line:
                continue

            newline = clean_text(line)
            k, v = newline.split(':', 1)
            return_val[k.strip().lower().replace(' ', '_')] = v.strip()
    return return_val


def clean_status(status_dict):
    for key in [k for k in status_dict.keys()]:
        if key not in status_headers:
            del status[key]
    return status


def export_unfolding_word(status_dict, git_dir, json_data, lang_code, github_organization, front_matter, back_matter):
    """
    Exports JSON data for each language into its own Github repo.
    """
    write_page(os.path.join(git_dir, 'obs-{0}.json'.format(lang_code)), json_data)
    write_page(os.path.join(git_dir, 'obs-{0}-front-matter.json'.format(lang_code)), front_matter)
    write_page(os.path.join(git_dir, 'obs-{0}-back-matter.json'.format(lang_code)), back_matter)

    write_page(os.path.join(git_dir, 'status-{0}.json'.format(lang_code)), clean_status(status_dict))
    write_page(os.path.join(git_dir, 'README.md'), OBS.get_readme_text())

    gitCreate(git_dir)
    name = 'obs-{0}'.format(lang_code)
    desc = 'Open Bible Stories for {0}'.format(lang_code)
    url = 'http://unfoldingword.org/{0}/'.format(lang_code)
    githubCreate(git_dir, name, desc, url, github_organization)
    commit_msg = str(status_dict)
    gitCommit(git_dir, commit_msg)
    gitPush(git_dir)


def uw_qa(obs, lang_code, status_dict):
    """
    Implements basic quality control to verify correct number of frames,
    correct JSON formatting, and correct status headers.
    """
    flag = True
    for header in status_headers:
        if header not in status_dict:
            print('==> !! Cannot export {0}, status page missing header {1}'.format(lang_code, header))
            flag = False

    if not obs.verify_all():
        flag = False

    return flag


def update_uw_admin_status_page():
    ObsPublishedLangs.update_page(ObsPublishedLangs.cat_url, ObsPublishedLangs.uw_stat_page)


def get_front_matter(lang_code, today_str):
    return_val = OBS.get_front_matter()
    return_val['language'] = lang_code
    return_val['date_modified'] = today_str

    front_path = os.path.join(pages, lang_code, 'obs', 'front-matter.txt')
    if os.path.exists(front_path):

        with codecs.open(front_path, 'r', encoding='utf-8') as in_file:
            front = in_file.read()

        for l in link_re.findall(front):
            if '|' in l:
                clean_url = l.split('|')[1].replace(']', '')
            else:
                clean_url = l.replace(']', '').replace('[', '')
            front = front.replace(l, clean_url)

        return_val['front-matter'] = front

        obs_name_se = obs_name_re.search(front)
        if obs_name_se:
            return_val['name'] = obs_name_se.group(1)

        tag_line_se = tag_line_re.search(front)
        if tag_line_se:
            return_val['tagline'] = tag_line_se.group(0).split('**')[1].strip()

    return return_val


def get_back_matter(lang_code, today_str):
    return_val = OBS.get_front_matter()
    return_val['language'] = lang_code
    return_val['date_modified'] = today_str

    back_path = os.path.join(pages, lang_code, 'obs', 'back-matter.txt')
    if os.path.exists(back_path):
        with codecs.open(back_path, 'r', encoding='utf-8') as in_file:
            back = in_file.read()

        return_val['back-matter'] = clean_text(back)

    return return_val


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-l', '--lang', dest="lang", default=False,
                        required=True, help="Language code of resource.")
    parser.add_argument('-e', '--export', dest="uwexport", default=False,
                        action='store_true', help="Export to unfoldingWord.")
    parser.add_argument('-t', '--testexport', dest="testexport", default=False,
                        action='store_true', help="Test export to unfoldingWord.")

    args = parser.parse_args(sys.argv[1:])
    lang = args.lang
    uw_export = args.uwexport
    test_export = args.testexport

    today = ''.join(str(datetime.date.today()).rsplit('-')[0:3])
    lang_dict = load_lang_strings()
    uw_cat_path = os.path.join(unfoldingWord_dir, 'obs-catalog.json')
    uw_catalog = load_json_object(uw_cat_path, [])
    uw_cat_langs = [x['language'] for x in uw_catalog]
    cat_path = os.path.join(export_dir, 'obs-catalog.json')
    catalog = load_json_object(cat_path, [])

    if 'obs' not in os.listdir(os.path.join(pages, lang)):
        print('OBS not configured in Door43 for {0}'.format(lang))
        sys.exit(1)
    app_words = get_json_dict(os.path.join(pages, lang, 'obs/app_words.txt'))
    lang_direction = 'ltr'
    if lang in rtl:
        lang_direction = 'rtl'
    obs_obj = OBS()
    obs_obj.app_words = app_words
    obs_obj.date_modified = today
    obs_obj.direction = lang_direction
    obs_obj.language = lang

    page_list = glob.glob('{0}/{1}/obs/[0-5][0-9].txt'.format(pages, lang))
    page_list.sort()
    for page in page_list:
        obs_obj.chapters.append(get_chapter(page, num_re.search(page).group(1)))

    obs_obj.chapters.sort(key=lambda frame: frame['number'])
    json_lang_file_path = os.path.join(export_dir, lang, 'obs', 'obs-{0}.json'.format(lang))
    prev_json_lang = load_json_object(json_lang_file_path, {})
    cur_json = json.dumps(obs_obj, sort_keys=True, cls=OBSEncoder)
    prev_json = get_dump(prev_json_lang)

    if lang not in lang_dict:
        print("Configuration for language {0} missing.".format(lang))
        sys.exit(1)

    status = get_json_dict(os.path.join(uwadmin_dir, lang, 'obs/status.txt'))
    if not status:
        status = OBS.get_status()

    lang_cat = {'language': lang,
                'string': lang_dict[lang],
                'direction': lang_direction,
                'date_modified': today,
                'status': status,
                }
    if lang not in [x['language'] for x in catalog]:
        catalog.append(lang_cat)

    if str(cur_json) != str(prev_json):
        ([x for x in catalog if x['language'] == lang][0]['date_modified']) = today
        write_page(json_lang_file_path, cur_json)

    if test_export:
        print('Testing {0} export...'.format(lang))
        front_json = get_front_matter(lang, today)
        back_json = get_back_matter(lang, today)
        if not uw_qa(obs_obj, lang, status):
            print('---> QA Failed.')
            sys.exit(1)
        print('---> QA Passed.')
        sys.exit()
    if uw_export:
        try:
            pw = open('/root/.github_pass', 'r').read().strip()
            g_user = githubLogin('dsm-git', pw)
            github_org = getGithubOrg('unfoldingword', g_user)
        except GithubException as e:
            print('Problem logging into Github: {0}'.format(e))
            sys.exit(1)

        unfolding_word_lang_dir = os.path.join(unfoldingWord_dir, lang)
        if 'checking_level' in status and 'publish_date' in status:
            if status['checking_level'] in ['1', '2', '3'] and status['publish_date'] == str(datetime.date.today()):
                print("==========")
                front_json = get_front_matter(lang, today)
                back_json = get_back_matter(lang, today)
                if not uw_qa(obs_obj, lang, status):
                    print("==========")
                    sys.exit(1)
                print("---> Exporting to unfoldingWord: {0}".format(lang))
                export_unfolding_word(status, unfolding_word_lang_dir, cur_json,
                                      lang, github_org, front_json, back_json)
                if lang in uw_cat_langs:
                    uw_catalog.pop(uw_cat_langs.index(lang))
                    uw_cat_langs.pop(uw_cat_langs.index(lang))
                uw_catalog.append(lang_cat)
                print("==========")

    cat_json = get_dump(catalog)
    write_page(cat_path, cat_json)
    if uw_export:
        uw_cat_json = get_dump(uw_catalog)
        write_page(uw_cat_path, uw_cat_json)
        update_uw_admin_status_page()
