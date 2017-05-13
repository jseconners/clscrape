craigdata
====================================================


pull craigslist post data from the command line
-------------------------------------------

craigdata pulls non-filtered post data from craigslist sections
(except discussion forums - for now) and prints results as json.

First things. If you try to run any of the other commands, you'll get
a response about the database file not existing. Run the `build` command
to build the database of available pages and sections
::

    $ craigdata build
    > Building database...
    > Success

Now you're ready. You can always run that command again if you accidentally
delete the database file stored in ~/.craigdata

Use the script's `pull` for pulling post data from a section's main page
and parsing back in time from the first post (i.e., latest) within
a specified window. The default window is 30 minutes. Below pulls the
last 30 minutes worth of posts from the San Diego page (43), free stuff (171).
::

    $ craigdata pull 43 171
    > DATE=`date +%Y-%m-%d`
    > [
    >   {
    >     "url": "https://sandiego.craigslist.org/csd/zip/6129099038.html",
    >     "date_time": "2017-05-12 13:49",
    >     "post_id": "6129099038",
    >     "title": "Windsurfing board"
    >   },
    >   {
    >     "url": "https://sandiego.craigslist.org/nsd/zip/6129094907.html",
    >     "date_time": "2017-05-12 13:46",
    >     "post_id": "6129094907",
    >     "title": "Free desk - very good condition!"
    >   },
    >   ...
    >   ...
    > ]

Where did those numbers come from? They're the ids for the page and section,
respectively. Use the list command to see available pages and sections and pipe to
a filter or pager to find the ids you need before pulling data
::

    $ craigdata list pages | less
    > 0  : US >> Alabama >> auburn
    > 1  : US >> Alabama >> birmingham
    > 2  : US >> Alabama >> dothan
    > 3  : US >> Alabama >> florence / muscle shoals
    > ...
    >
    $ craigdata list pages | grep 'California'
    > 26 : US >> California >> bakersfield
    > 27 : US >> California >> chico
    > 28 : US >> California >> fresno / madera
    > ...
    >
    $ craigdata list pages | grep 'san diego'
    > 43 : US >> California >> san diego
    >
    $ craigdata list sections | less
    > 0  : community
    > 1  : community >> activities
    > 2  : community >> artists
    > ...
    >
    $ craigdata list sections | grep 'motorcycles'
    > 179: for sale >> motorcycles >> Motorcycles >> ALL MOTORCYCLES
    > 180: for sale >> motorcycles >> Motorcycles >> BY-OWNER ONLY
    > 181: for sale >> motorcycles >> Motorcycles >> BY-DEALER ONLY
    > 182: for sale >> motorcycles >> Parts & Accessories >> ALL PARTS & ACCESSORIES
    > ...

There are a couple options for pulling post data. The first command above shows
using pull with the default behavior: getting all post data 30 minutes back from
the most recent post. You can change that window using the `-w` option. The acceptable
time window formats are: #:# (hrs:mins), # (hrs) or :# (minutes).
::

    $ craigdata 43 171 -w 1:22   # 1 hour and 22 minute window
    $ craigdata 43 171 -w 2      # 2 hour window
    $ craigdata 43 171 -w :45    # 45 minute window

By default, a shallow data scrape is done from the post listings page. Use the -d (deep)
option to have the script visit each post page and additionally pull the description
and attributes, if available.

::

    $ craigdata 43 171 -w :2 -d
    > [
    >   {
    >     "date_time": "2017-05-12 14:17",
    >     "description": "** LOW MILES ** Excellent Suzuki Boulevard M50 805cc with Cobra exhaust.",
    >     "post_id": "6129140162",
    >     "url": "https://sandiego.craigslist.org/esd/mcy/6129140162.html",
    >     "attributes": {
    >        "title status": "clean",
    >        "engine displacement (CC)": "805",
    >        "odometer": "10951",
    >        "transmission": "manual",
    >        "paint color": "grey",
    >        "fuel": "gas",
    >        "condition": "excellent"
    >     },
    >     "title": "2006 Suzuki Boulevard M50 805cc **Low miles**"
    >   }
    > ]


Installation
------------
::

    python setup.py install

craigdata requires lxml, which requires the libxml2 and libxslt libraries. If these aren't installed already
setuptools will give you and error trying to install lxml. See the requirements page for lxml:
http://lxml.de/installation.html

Usage
-----
craigdata has three sub-commands: pull, list and rebuild. Run `craigdata <pull|list|rebuild> -h`
to see help specific to that sub-command.

pull
::

    usage: craigdata pull [-h] [-d] [-w WINDOW] pid sid

    positional arguments:
      pid                   page id
      sid                   section id

    optional arguments:
      -h, --help            show this help message and exit
      -d, --deep            go deep, visit post page and get more fields
      -w WINDOW, --window WINDOW
                            time window back from most recent post, # (hrs), #:#
                            (hrs:mins), :# (mins). default is :30 (30 mins)
list
::

    usage: craigdata list [-h] {pages,sections}

    positional arguments:
      {pages,sections}  what to list from the db

    optional arguments:
      -h, --help        show this help message and exit

build
::

    usage: craigdata build [-h]

    optional arguments:
      -h, --help  show this help message and exit

Author
------

-  James Conners


Development
-----------

-  Checkout the repo
-  Run `python -m craigdata.craigdata` (if you try running `python craigdata/craigdata.py` you my get `ValueError: Attempted relative import in non-package`).


