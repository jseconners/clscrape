#!/usr/bin/env python

######################################################
#
# craigdata - pull post data from craiglist from the
# command line.
# Written by James Conners (jseconners@gmail.com)
#
######################################################

import sys
import os
import json
import argparse
import requests
from datetime import datetime, timedelta
from urlparse import urljoin
from fake_useragent import UserAgent

import xpathtpl
from .templates import pages_tpl, sections_tpl, submenu_tpl_a, submenu_tpl_b


DB_DIR = os.path.join(os.path.expanduser('~'), '.craigdata')
DB_FILE = os.path.join(DB_DIR, 'db.json')
BASE_URL = 'https://www.craigslist.org/about/sites'
SKIP_SECTIONS = [
    'discussion forums'
]
POST_DATA = []
UA = UserAgent()


def _page_content(url):
    """ Get page content for url as binary string """
    try:
        return requests.get(url, headers={'User-Agent': UA.random}).content
    except requests.exceptions.RequestException as e:
        print e
        sys.exit(1)


def load_db():
    """ Load the database file """
    if not os.path.exists(DB_FILE):
        print("Database file {} doesn't exist \n"
              "Run `craigdata build` to build database.".format(DB_FILE))
        sys.exit(1)
    return json.load(open(DB_FILE))


def build_db():
    """ Build the pages/sections database and write to file """
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    # get a list of all craigslist pages
    pages = xpathtpl.parse(_page_content(BASE_URL), pages_tpl)
    pages_list = []
    for p in pages['pages']:
        country = p['country']
        for s in p['states']:
            state = s['name']
            for c in s['cities']:
                pages_list.append([country, state, c['name'], c['href']])

    # make a list of all sections
    first_url = pages_list[0][-1]
    sections = xpathtpl.parse(_page_content(first_url), sections_tpl)
    sections_list = []
    for s in sections['sections']:
        section = s['name']
        # this section has a top-level page
        if len(s['href']):
            sections_list.append([section, s['href']])
        for ss in s['sub-sections']:
            subsection = ss['name']
            # sub section leads to search page
            if ss['href'].startswith('/search/'):
                sections_list.append([section, subsection, ss['href']])
            else:
                submenu_page = _page_content(urljoin(first_url, ss['href']))
                sub_a = xpathtpl.parse(submenu_page, submenu_tpl_a)
                sub_b = xpathtpl.parse(submenu_page, submenu_tpl_b)
                if len(sub_a['sections']):
                    for header in sub_a['sections']:
                        title = header['name']
                        for sss in header['sub-sections']:
                            sections_list.append([section, subsection, title, sss['name'], sss['href']])
                if len(sub_b['sections']):
                    for sss in sub_b['sections']:
                        sections_list.append([section, subsection, sss['name'], sss['href']])

    for s in sections_list:
        print s
    sys.exit()
    # parse sections using the first available main page
    section_paths = _parse_sections(page_paths[0][-1])

    db_structure = json.dumps({
        'pages': page_paths,
        'sections': section_paths
    }, indent=4, separators=(',', ': '))

    # Write configs to file
    try:
        open(DB_FILE, 'w').write(db_structure)
    except IOError:
        print("Error, could not write db file: {}".format(DB_FILE)) >> sys.stderr
        sys.exit(1)

    print("Parsed {} total Craigslist pages".format(len(page_paths)))
    print("Parsed {} total sections".format(len(section_paths)))


def _display_paths(records):
    """ Display structured content from the database file """
    for (i, p) in enumerate(records):
        format_string = "{:<3}: " + " >> ".join([j for j in p[:-1]])
        print(format_string.format(i, *p).encode('utf-8'))


def get_parser():
    parser = argparse.ArgumentParser(description='craigslist post data puller')
    subparsers = parser.add_subparsers(title='commands', dest='command')

    subparsers.add_parser('build', help='build page/section database file')

    list_parser = subparsers.add_parser('list', help='list pages or sections')
    list_parser.add_argument('what', choices=['pages', 'sections'],
                             help='what to list from the db')

    pull_parser = subparsers.add_parser('pull', help='pull some post data')
    pull_parser.add_argument('pid', type=int, help='page id')
    pull_parser.add_argument('sid', type=int, help='section id')
    pull_parser.add_argument('-d', '--deep', help='go deep, visit post page and get more fields',
                             action='store_true')
    pull_parser.add_argument('-w', '--window', type=str, default=':30',
                             help='time window back from most recent post, # (hrs), #:# (hrs:mins), :# (mins). '
                                  'default is :30 (30 mins)')
    return parser


def parse_time_window(window):
    """ Parse the specified time window and return as (float) minutes, or None if invalid """
    regexps = {
        '^(\d+):?$': lambda match: float(match.group(1)) * 60,
        '^(\d+):(\d+)$': lambda match: float(match.group(1)) * 60 + float(match.group(2)),
        '^:(\d+)$': lambda match: float(match.group(1))
    }
    for r in regexps:
        m = re.match(r, window)
        if m:
            return regexps[r](m)
    return None


def parse_post_attributes(post_page):
    """ Parse the attributes section of a post page into a dictionary """
    attributes = []
    for att in post_page.xpath('//p[@class="attrgroup"]/span'):
        parts = tuple([p.strip() for p in att.text_content().split(':')])
        if len(parts) != 2:
            continue
        attributes.append(parts)
    return dict(attributes)


def get_post_data(url):
    """ Parse data from the actual post page """
    post_page = lxml.html.fromstring(requests.get(url).content)
    row = {
        'description': __get_first(post_page, '//meta[@name="description"]/@content'),
        'attributes': parse_post_attributes(post_page)
    }
    return row


def get_data(url, window, deep=False):
    """ Given the main page url for a section, parse and store the post data from the
    most recent (i.e., first) post backward within the specified time window (minutes).
    If deep=True, visit each post page for extra data.
    """

    page = lxml.html.fromstring(requests.get(url).content)
    posts = page.xpath("//p[@class='result-info']")

    # Don't want to go into next-page else block if there
    # are no posts on this page
    if not len(posts):
        return

    end_datetime = None
    for post in posts:
        row = {
            'date_time': post.xpath("time")[0].attrib['datetime']
        }
        post_datetime = datetime.strptime(row['date_time'], '%Y-%m-%d %H:%M')

        # Set the end and begin datetime for window from first post
        if end_datetime is None:
            begin_datetime = post_datetime
            end_datetime = begin_datetime - timedelta(minutes=window)

        # End parsing if we've reached the end of tme window
        if post_datetime < end_datetime:
            break

        title = __get_first(post, "a[@class='result-title hdrlnk']")
        row['title'] = title.text_content()
        row['neighborhood'] = __get_first(post, 'span[@class="result-meta"]/span[@class="result-hood"]/text()'),
        row['price'] = __get_first(post, 'span[@class="result-meta"]/span[@class="result-price"]/text()')
        row['url'] = urljoin(url, title.attrib['href'])
        row['post_id'] = title.attrib['data-id']

        tags = __get_first(post, 'span[@class="result-meta"]/span[@class="result-tags"]/text()')
        if tags is not None:
            row['tags'] = tags.split()
        else:
            row['tags'] = []

        # Go deep and pull more fields from post page
        if deep:
            post_data = get_post_data(row['url'])
            row.update(post_data)

        POST_DATA.append(row)
    else:
        # Reached the end of the page, but not the time window.
        # Adjust the time window based on how far we've traversed
        # and start parsing the next page if available.
        adjusted_window = window - ((begin_datetime - post_datetime).total_seconds() / 60.0)
        next_links = page.xpath('//a[@class="button next"]')
        if len(next_links):
            next_url = urljoin(url, next_links[0].attrib['href'])
            get_data(next_url, adjusted_window, deep)


def command_line_runner():
    parser = get_parser()
    args = vars(parser.parse_args())

    if args['command'] == 'build':
        print("Building database...")
        build_db()
        print("Success")
        return

    # Load pages and sections database
    db = load_db()

    # list pages or sections
    if args['command'] == 'list':
        _display_paths(db[args['what']])
        return

    window = parse_time_window(args['window'])
    if window is None:
        print("Window must be of the format: #:# (hrs:mins), # (hrs) or :# (mins)")
        return
    try:
        page = db['pages'][args['pid']]
    except IndexError:
        print("No page with id: {}".format(args['pid']))
        return
    try:
        section = db['sections'][args['sid']]
    except IndexError:
        print("No section with id: {}".format(args['sid']))
        return

    # make url and start parsing posts
    url = page[-1].rstrip('/') + section[-1]
    get_data(url, window, args['deep'])

    # output results as json
    print(json.dumps(POST_DATA, indent=4, separators=(',', ': ')))


if __name__ == '__main__':
    command_line_runner()
