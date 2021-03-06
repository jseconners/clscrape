#!/usr/bin/env python

from setuptools import setup, find_packages
import clscrape
import os


def extra_dependencies():
    import sys
    ret = []
    if sys.version_info < (2, 7):
        ret.append('argparse')
    return ret


def read(*names):
    values = dict()
    extensions = ['.txt', '.rst']
    for name in names:
        value = ''
        for extension in extensions:
            filename = name + extension
            if os.path.isfile(filename):
                value = open(name + extension).read()
                break
        values[name] = value
    return values

long_description = """
%(README)s

News
====

%(CHANGES)s

""" % read('README', 'CHANGES')

setup(
    name='clscrape',
    version=clscrape.__version__,
    description='Command line craiglist scraper',
    long_description=long_description,
    keywords='web scraping craigslist data console command line',
    author='James Conners',
    author_email='jseconners@gmail.com',
    maintainer='James Conners',
    maintainer_email='jseconners@gmail.com',
    url='https://github.com/jseconners/craigdata',
    license='MIT',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'clscrape = clscrape.clscrape:command_line_runner',
        ]
    },
    install_requires=[
        'beautifulsoup4',
        'requests'
    ] + extra_dependencies(),
)
