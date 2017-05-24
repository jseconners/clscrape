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
import lxml.html
import re
from datetime import datetime, timedelta
from urlparse import urljoin


DB_DIR = os.path.join(os.path.expanduser('~'), '.craigdata')
DB_FILE = os.path.join(DB_DIR, 'db.json')
BASE_URL = 'https://www.craigslist.org/about/sites'
SKIP_SECTIONS = [
    'discussion forums'
]
POST_DATA = []


def __get_first(html_obj, xpath):
    """ Get first element returned from xpath expression, if available """
    res = html_obj.xpath(xpath)
    if len(res):
        return res[0]
    else:
        return None


def _get_page_obj(url):
    """ Return page at url as object created from lxml.html.fromstring """
    try:
        res = requests.get(url)
    except requests.exceptions.RequestException:
        print("Failed retrieving {}".format(url)) >> sys.stderr
        sys.exit(1)
    return lxml.html.fromstring(res.content)


def _parse_pages(url):
    """ Parse all available pages from sites page """
    paths = []
    page = _get_page_obj(url)
    for region in page.xpath('//h1'):
        region_name = region.text_content()
        for sub_region in region.getnext().xpath('div/h4'):
            sub_region_name = sub_region.text
            for place in sub_region.getnext().xpath('li/a'):
                place_name = place.text
                paths.append([region_name, sub_region_name, place_name, place.attrib['href']])
    return paths


def _parse_submenu_page(url):
    """ Parse section submenu page, e.g. 'by owner', 'by dealer' or like personals etc. """
    page = _get_page_obj(url)

    paths = []
    # This is the 'by owner', 'by dealer', etc. type
    for h3 in page.xpath('//section[@class="body"]/div[@class="leftside"]/h3'):
        header = h3.text.rstrip(':')
        ul = h3.getnext()
        for li_a in ul.xpath('li/a'):
            section = li_a.text
            section_href = li_a.attrib['href']
            paths.append([header, section, section_href])
    # Everything else. Just find all the links to valid post pages
    else:
        for section_link in page.xpath('//section[@class="body"]//a'):
            section = section_link.text_content()
            section_href = section_link.attrib['href']
            if re.search('/search/\w+', section_href):
                paths.append([section, section_href])
    return paths


def _parse_sections(url):
    """ Parse sections from a location's main page """
    page = _get_page_obj(url)

    paths = []
    # Loop through section headers
    # e.g., jobs, for sale, etc.
    for header in page.xpath("//h4[@class='ban']"):
        section = header.text_content()
        if section in SKIP_SECTIONS:
            continue

        # Add link to aggregate section page if available
        section_link = __get_first(header, 'a')
        if section_link is not None:
            paths.append([section, section_link.attrib['href']])

        # Parse subsections
        subsection_div = header.getnext()
        # Go through sub sections
        # e.g. motorcycles, boats, etc.
        for subsection_link in subsection_div.xpath('ul/li/a'):
            subsection = subsection_link.text_content()
            subsection_href = subsection_link.attrib['href']

            # sub section link leads straight to search results
            if subsection_href.find('/search/') == 0:
                paths.append([section, subsection, subsection_href])
            # sub section link leads to another submenu page
            else:
                for submenu_path in _parse_submenu_page(urljoin(url, subsection_href)):
                    paths.append([section, subsection] + submenu_path)
    return paths


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
