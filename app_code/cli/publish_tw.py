from __future__ import print_function, unicode_literals
import argparse
import codecs
import glob
import os
import re
import datetime
import sys
import shutil
import tempfile
from general_tools.file_utils import write_file, unzip
from general_tools.print_utils import print_ok, print_notice
from general_tools.url_utils import join_url_parts, download_file
from uw.update_catalog import update_catalog

api_v2 = '/var/www/vhosts/api.unfoldingword.org/httpdocs/ts/txt/2/'
tw_aliases = {}
tw_re = re.compile(r'^# (.*?)( #|\s$)', re.UNICODE | re.MULTILINE)
def_re = re.compile(r'## (Definition|Facts|Description):? ##(.*?)\n[#(]', re.UNICODE | re.DOTALL)
sub_re = re.compile(r'\n### (.*) ###\n', re.UNICODE)
link_name_re = re.compile(r'\[([A-Za-z0-9\-]*)\]\(', re.UNICODE)
cf_re = re.compile(r'See also.*', re.UNICODE)
suggest_re = re.compile(r'## Translation Suggestions:? ##(.*?)[#(][TS]?', re.UNICODE | re.DOTALL)
bold_re = re.compile(r'\*\*(.*?)\*\*', re.UNICODE)
li_re = re.compile(r'^ *\* ', re.UNICODE | re.MULTILINE)
h3_re = re.compile(r'\n#### (.*?) ####\n', re.UNICODE)

# remember these so we can delete them
download_dir = ''

# for getting aliases from tN
it_re = re.compile(r'==== translationWords: ====(.*?)====', re.UNICODE | re.DOTALL)
link_re = re.compile(r':([^:]*\|.*?)\]\]', re.UNICODE)


def main(date_today, tag, version):
    """

    :param str|unicode date_today:
    :param str|unicode tag:
    :param str|unicode version:
    :return:
    """
    global download_dir, tw_aliases

    repo = 'https://git.door43.org/Door43/en-tw'
    download_dir = tempfile.mkdtemp(prefix='tempTW_')
    download_url = join_url_parts(repo, 'archive', '{0}.zip'.format(tag))
    downloaded_file = os.path.join(download_dir, 'tW.zip')

    # download the repository
    try:
        print('Downloading {0}...'.format(download_url), end=' ')
        download_file(download_url, downloaded_file)
    finally:
        print('finished.')

    try:
        print('Unzipping...'.format(downloaded_file), end=' ')
        unzip(downloaded_file, download_dir)
    finally:
        print('finished.')

    # examine the repository
    tw_list = []
    for root, dirs, files in os.walk(os.path.join(download_dir, 'en-tw', 'content')):
        for f in files:
            file_name = os.path.join(root, f)
            tw = get_tw(file_name)
            if tw:
                tw_list.append(tw)

    for i in tw_list:  # type: dict
        if i['id'] in tw_aliases:
            i['aliases'] = [x for x in tw_aliases[i['id']] if x != i['term']]

    tw_list.sort(key=lambda y: len(y['term']), reverse=True)
    tw_list.append({'date_modified': date_today, 'version': version})
    api_path = os.path.join(api_v2, 'bible', 'en')
    write_file('{0}/terms.json'.format(api_path), tw_list, indent=2)

    print()
    print('Updating the catalogs...', end=' ')
    update_catalog()
    print('finished.')


def get_tw(f):
    with codecs.open(f, 'r', encoding='utf-8-sig') as in_file:
        page = in_file.read()

    # The filename is the ID
    tw = {'id': f.rsplit('/', 1)[1].replace('.md', '')}
    tw_se = tw_re.search(page)
    if not tw_se:
        print('Term not found for {}'.format(tw['id']))
        return False
    tw['term'] = tw_se.group(1).strip()
    tw['sub'] = get_tw_sub(page)
    tw['def_title'], tw['def'] = get_tw_def(page)
    if not tw['def_title']:
        print('Definition or Facts not found for {}'.format(tw['id']))
        return False
    tw['cf'] = get_tw_cf(page)
    tw['def'] += get_tw_suggestions(page)
    return tw


def get_tw_def(page):
    def_se = def_re.search(page)
    if def_se:
        def_txt = def_se.group(2).rstrip()
        return def_se.group(1), get_html(def_txt)

    # if you are here, the tw def was not found
    return False, False


def get_tw_sub(page):
    sub = ''
    sub_se = sub_re.search(page)
    if sub_se:
        sub = sub_se.group(1)
    return sub.strip()


def get_tw_cf(page):
    cf = []
    cf_se = cf_re.search(page)
    if cf_se:
        text = cf_se.group(0)
        cf = [x.group(1) for x in link_name_re.finditer(text)]
    return cf


def get_tw_suggestions(page):
    sug_format = '<h2>Translation Suggestions</h2>{0}'
    sug_se = suggest_re.search(page)
    if not sug_se:
        return ''
    sug_txt = sug_format.format(sug_se.group(1).rstrip())
    return get_html(sug_txt)


def get_html(text):
    # add ul/li
    text = bold_re.sub(r'<b>\1</b>', text)
    text = h3_re.sub(r'<h3>\1</h3>', text)
    text = get_html_list(text)
    return text.strip()


def get_html_list(text):
    started = False
    new_text = []
    for line in text.split('\n'):
        if li_re.search(line):
            if not started:
                started = True
                new_text.append('<ul>')
            line = li_re.sub('<li>', line)
            new_text.append('{0}</li>'.format(line))
        else:
            if started:
                started = False
                new_text.append('</ul>')
            new_text.append(line)
    if started:
        new_text.append('</ul>')
    return ''.join(new_text)


def get_aliases():
    root = '/var/www/vhosts/door43.org/httpdocs/data/gitrepo'
    pages = os.path.join(root, 'pages')
    tn_path = os.path.join(pages, 'en', 'bible/notes')
    for book in os.listdir(tn_path):
        book_path = os.path.join(tn_path, book)
        if len(book) > 3:
            continue
        if not os.path.isdir(book_path):
            continue

        for chapter in os.listdir(book_path):
            try:
                int(chapter)
            except ValueError:
                continue
            for f in glob.glob('{0}/{1}/*.txt'.format(book_path, chapter)):
                if 'home.txt' in f:
                    continue
                if '00/intro.txt' in f:
                    continue
                page = codecs.open(f, 'r', encoding='utf-8').read()
                get_aliases_from_page(page, f)


def get_aliases_from_page(page, f):
    global tw_aliases
    it_se = it_re.search(page)
    if not it_se:
        if not f.endswith(('/00.txt', '/000.txt')):
            print('Terms not found for {0}'.format(f))

        return

    text = it_se.group(1).strip()
    its = link_re.findall(text)
    for t in its:
        term, alias = t.split(str('|'))
        if term not in tw_aliases:
            tw_aliases[term] = []
        if alias and alias not in tw_aliases[term]:
            tw_aliases[term].append(alias)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--version', dest='version', default=False,
                        required=True, help='The version number of this resource.')
    parser.add_argument('-t', '--tag', dest='tag', default='master',
                        required=False, help='Branch or tag to use as the source. Default is master.')

    args = parser.parse_args(sys.argv[1:])
    today = ''.join(str(datetime.date.today()).rsplit(str('-'))[0:3])

    try:
        print_ok('STARTING: ', 'publishing tW repository.')
        get_aliases()
        main(today, args.tag, args.version)
        print_ok('ALL FINISHED: ', 'publishing tW repository.')
        print_notice('Don\'t forget to notify the interested parties.')

    finally:
        # delete temp files
        if os.path.isdir(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
