#!/usr/bin/env python

from setuptools import setup, find_packages
import craigdata
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
    name='craigdata',
    version=craigdata.__version__,
    description='Craigslist post data from the command line',
    long_description=long_description,
    keywords='craigdata craigslist posts data console command line',
    author='James Conners',
    author_email='jseconners@gmail.com',
    maintainer='James Conners',
    maintainer_email='jseconners@gmail.com',
    url='https://github.com/jseconners/craigdata',
    license='MIT',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'craigdata = craigdata.craigdata:command_line_runner',
        ]
    },
    install_requires=[
        'beautifulsoup4',
        'requests'
    ] + extra_dependencies(),
)
