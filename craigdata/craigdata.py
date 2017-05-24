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
import re
from datetime import datetime, timedelta
from urlparse import urljoin

from bs4 import BeautifulSoup
import requests

DB_DIR = os.path.join(os.path.expanduser('~'), '.craigdata')
DB_FILE = os.path.join(DB_DIR, 'db.json')
BASE_URL = 'https://www.craigslist.org/about/sites'
SKIP_SECTIONS = [
    'discussion forums'
]
POST_DATA = []


def _get_soup(url):
    """ Return BeautifulSoup parser for page """
    try:
        res = requests.get(url)
    except requests.exceptions.RequestException:
        print("Failed retrieving {}".format(url)) >> sys.stderr
        sys.exit(1)
    return BeautifulSoup(res.content, 'html.parser')


def _display_paths(records):
    """ Display structured content from the database file """
    for (i, p) in enumerate(records):
        format_string = "{:<3}: " + " >> ".join([j for j in p[:-1]])
        print(format_string.format(i, *p).encode('utf-8'))


def _get_t(elm):
    """ helper function, get text if element exists """
    return elm.text.strip() if elm is not None else elm


def _get_a(elm, a):
    """ helper function, get attribute if element exists """
    return elm.get(a) if elm is not None else elm


def _parse_pages(url):
    """ Parse all craigslist pages from /about page """
    sp = _get_soup(url)
    pages = []
    for h1 in sp('h1'):
        country = h1.text
        for h4 in h1.find_next("div").find_all('h4'):
            state = h4.text
            for a in h4.find_next("ul").find_all('a'):
                pages.append([country, state, a.text, a.get('href')])
    sp.decompose()
    return pages


def _parse_sections(url, skip=[]):
    """ Parse all available sections from any craigslist page """
    sp = _get_soup(url)
    sections = []
    for h4 in sp('h4', class_='ban'):
        section = h4.text
        if section in skip:
            continue
        if h4.a:
            sections.append([section, h4.a.get('href')])
        for a in h4.find_next('div').find_all('a'):
            cat = a.text
            href = a.get('href')
            if href.startswith('/search/'):
                sections.append([section, cat, href])
            else:
                submenu_url = urljoin(url, href)
                for submenu_section in _parse_section_submenu(submenu_url):
                    sections.append([section, cat] + submenu_section)
    sp.decompose()
    return sections


def _parse_section_submenu(url):
    """ Parse category submenu page, i.e. bikes (by owner, etc.) """
    sp = _get_soup(url)
    # two types of submenus, identified by link container div
    submenu_a = sp.find('div', class_='leftside')
    submenu_b = sp.find('div', class_='links')
    submenu_sections = []
    if submenu_a:
        for h3 in submenu_a.find_all('h3'):
            cat = h3.text
            for a in h3.find_next('ul').find_all('a'):
                subcat = a.text
                href = a.get('href')
                submenu_sections.append([cat, subcat, href])
    elif submenu_b:
        for a in submenu_b.find_all('a'):
            cat = a.text
            href = a.get('href')
            submenu_sections.append([cat, href])
    sp.decompose()
    return submenu_sections


def _parse_post_page(url):
    """ get full description and optional attributes from post page """
    sp = _get_soup(url)
    post_data = {
        'description': _get_a(sp.find('meta', {'name': 'description'}), 'content')
    }
    attributes = []
    for p in sp('p', class_='attrgroup'):
        for span in p.find_all('span'):
            parts = tuple([p.strip() for p in span.text.split(':')])
            if len(parts) != 2:
                continue
            attributes.append(parts)
    post_data['attributes'] = dict(attributes)
    sp.decompose()
    return post_data


def _parse_post(post, url):
    # reliable post data
    title_tag = post.find('a', class_='result-title hdrlnk')
    time_tag = post.find('time')

    data = {
        'date_time': time_tag.get('datetime'),
        'title': title_tag.text.strip(),
        'post-id': title_tag.get('data-id'),
        'url': urljoin(url, title_tag.get('href')),
        # data that may not exist
        'neighborhood': _get_t(post.find('span', class_='result-hood')),
        'price': _get_t(post.find('span', class_='result-price')),
        'tags': _get_t(post.find('span', class_='result-tags'))
    }
    data['tags'] = data['tags'].split() if data['tags'] else []
    return data


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
    page_paths = _parse_pages(BASE_URL)
    # parse sections using the first available main page
    section_paths = _parse_sections(page_paths[0][-1])

    db_structure = json.dumps({
        'pages': page_paths,
        'sections': section_paths
    }, indent=4, separators=(',', ': '))

    # Write to file
    try:
        open(DB_FILE, 'w').write(db_structure)
    except IOError:
        print("Error, could not write db file: {}".format(DB_FILE)) >> sys.stderr
        sys.exit(1)

    print("Parsed {} total Craigslist pages".format(len(page_paths)))
    print("Parsed {} total sections".format(len(section_paths)))


def get_data(url, window, deep=False):
    """ Given the main page url for a section, parse and store the post data from the
    most recent (i.e., first) post backward within the specified time window (minutes).
    If deep=True, visit each post page for extra data.
    """
    sp = _get_soup(url)

    end_datetime = None
    for post in sp.find_all('p', class_='result-info'):
        # parse post data
        data = _parse_post(post, url)

        # Set the end and begin datetime for window from first post
        post_datetime = datetime.strptime(data['date_time'], '%Y-%m-%d %H:%M')
        if end_datetime is None:
            begin_datetime = post_datetime
            end_datetime = begin_datetime - timedelta(minutes=window)

        # End parsing if we've passed the end of tme window
        if post_datetime < end_datetime:
            return

        # Go deep and pull more fields from post page
        if deep:
            data.update(_parse_post_page(data['url']))

        POST_DATA.append(data)

    # decompose parser
    sp.decompose()

    if end_datetime is not None:
        # Reached the end of the page, but not the time window.
        # Adjust the time window based on how far we've traversed
        # and start parsing the next page if available.
        traversed = ((begin_datetime - post_datetime).total_seconds() / 60.0)
        adjusted_window = window - traversed
        next_link = page.find('a', class_='button next')
        if next_link:
            next_url = urljoin(url, next_link.get('href'))
            get_data(next_url, adjusted_window, deep)


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
    pull_parser.add_argument('-d', '--deep',
                            help='go deep, visit post page and get more fields',
                             action='store_true')
    pull_parser.add_argument('-w', '--window', type=str, default=':30',
                             help='time window back from most recent post, '
                                  '# (hrs), #:# (hrs:mins), :# (mins). '
                                  'default is :30 (30 mins)')
    return parser


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
