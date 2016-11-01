# crossweb-trello
A small tools to automate adding events from Crossweb.pl to Trello.com list and archiving outdated


## Requirements

Application require Python 2.7 and some Python libraries.

## Installation

Install python 2.7: ``sudo apt-get install python2.7 python2.7-dev python-pip``

Install python dependencies: ``pip install -r requirements.txt``

## Usage

    usage: fetch.py [-h] [--city CITY] --board BOARD [--list LIST]
                    [--antyflood ANTYFLOOD] [--archive-only | --add-only]

    optional arguments:
      -h, --help            show this help message and exit
      --city CITY           A city for which download events (defaults all)
      --board BOARD         A board ID or shortlink in the Trello
      --list LIST           A list name in the Trello (default:"Events")
      --antyflood ANTYFLOOD
                            A limit of created cards once a run
      --archive-only        A switch to only archive on run
      --add-only            A switch to only add cards on run
