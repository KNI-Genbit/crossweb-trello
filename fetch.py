#!/bin/python
# -*- coding: utf-8 -*-
import argparse
import logging
import os
from datetime import datetime
from urllib2 import HTTPError

import dateutil.parser
from bs4 import BeautifulSoup
from trello import TrelloApi

URL = "http://195.149.225.176/wydarzenia/"
EXTRA_HEADERS = {'Host': 'crossweb.pl'}

DESCRIPTION_TEMPLATE = u"""
Data: {date}
Tytuł: {title}
Miasto: {city}
Temat: {topic}
Typ: {type}
Koszt: {cost}
Link: {link}
"""

try:
    TRELLO_APP_KEY = open('.app_key.txt').read().strip()
except IOError:
    TRELLO_APP_KEY = raw_input("Please enter Trello app key (see https://trello.com/app-key): ")
    open('.app_key.txt', 'wb').write(TRELLO_APP_KEY)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def get_session():
    if 'CACHE_REQUESTS' in os.environ:
        import requests_cache
        return requests_cache.CachedSession()
    import requests
    return requests.Session()


def trello_init():
    trello = TrelloApi(TRELLO_APP_KEY)
    try:
        trello.set_token(open('.token.txt').read().strip())
    except IOError:
        token_url = trello.get_token_url('Trello ', expires='never', write_access=True)
        print "Enter following URL in your browser:", token_url
        token = raw_input("Enter token please:")
        open('.token.txt', 'w').write(token)
        trello.set_token(token)
    return trello


def build_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city",
                        default='ALL',
                        help="A city for which download events (defaults all)")
    parser.add_argument("--board",
                        help="A board ID or shortlink in the Trello",
                        required=True)
    parser.add_argument("--list",
                        help='A list name in the Trello (default:"Events")',
                        default="Wydarzenia")
    parser.add_argument("--antyflood",
                        required=False,
                        type=int,
                        help="A limit of created cards once a run",
                        default=5)

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--archive-only",
                       action="store_true",
                       help="A switch to only archive on run")
    group.add_argument("--add-only",
                       action="store_true",
                       help="A switch to only add cards on run")

    return parser.parse_args()


def fetch_events(city=None):
    params = {} if not city or city is'ALL' else {'miasto': city}
    html = get_session().get(URL, params=params, headers=EXTRA_HEADERS).text
    logger.info("Fetching events from Crossweb")
    if 'Please complete the security check to access' in html:
        raise Exception("Cloudflare protection enabled")
    soup = BeautifulSoup(html, "lxml")
    for brow in soup.select('a.brow'):
        date = brow.select_one('.colDataDay').text + ".2016"
        date = datetime.strptime(date, '%d.%m.%Y')
        cost = brow.select_one('.cost').text
        is_free = 'bezp' in cost.lower()
        yield {'link': brow['href'],
               'date': date,
               'title': brow.select_one('.title').text.strip(),
               'city': brow.select_one('.city').text.strip(),
               'topic': brow.select_one('.topic').text.strip(),
               'type': brow.select_one('.type').text.strip(),
               'cost': cost.strip(),
               'is_free': is_free}


def get_board_id(trello, board):
    try:
        return trello.boards.get(board)['id']
    except HTTPError:
        raise Exception("Incorrect board. Update board ID, please!")


def get_list_id(trello, idBoard, listName):
    List = [x for x in trello.boards.get_list(idBoard) if x['name'] == listName]
    if not List:
        logger.debug("Unable to detect list. Create a new one!")
        return trello.lists.new(name=listName, idBoard=idBoard)['id']
    return List[0]['id']


def get_card_for_event(cards, event):
    cards = [card for card in cards
             if event['link'] in card['desc']]
    if cards:
        return cards[0]
    return None


def add_missing_cards(trello, city, idList, antyflood=5):
    cards = trello.lists.get_card_filter('all', idList)
    limit = antyflood
    for event in fetch_events(city):
        card = get_card_for_event(cards, event)
        if not card and datetime.now() > event['date']:
            logger.debug("Skip create old card for", event['title'])
        elif not card:
            description = DESCRIPTION_TEMPLATE.format(**event)
            card = trello.lists.new_card(idList, event['title'], desc=description)
            trello.cards.update_due(card['id'], event['date'].isoformat())
            if event['is_free']:
                trello.cards.new_label(card['id'], 'green')
            limit -= 1
            logger.info(u"Created card {title} for {link}".format(title=event['title'],
                                                                  link=event['link']))
        else:
            logger.info(u"Card {name} ({url}) for event".format(name=card['name'],
                                                                url=card['url']) +
                        u" {title} ({link}) detected!".format(title=event['title'],
                                                              link=event['link']))
        if not limit:
            logger.info("Anty-flood limit of cards added reached!")
            break


def archive_due_cards(trello, idList):
    cards = trello.lists.get_card_filter('open', idList)
    for card in cards:
        if not card['due']:
            logger.debug("Skip card {name} because of not due date".format(name=card['name']))
            continue
        due = dateutil.parser.parse(card['due'])
        if datetime.now() > due.replace(tzinfo=None):
            trello.cards.update_closed(card['id'], 'true')
            logger.info("Closed old card {name} ({url})".format(name=card['name'],
                                                                url=card['url']))
        else:
            logger.debug("Skip fresh card {name} ({url})".format(name=card['name'],
                                                                 url=card['url']))


def main():
    args = build_args()
    trello = trello_init()
    idBoard = get_board_id(trello, args.board)
    idList = get_list_id(trello, idBoard, args.list)
    if not args.archive_only:
        logger.info("Started adding missing cards")
        add_missing_cards(trello, args.city, idList, args.antyflood)
    if not args.add_only:
        logger.info("Archived old cards")
        archive_due_cards(trello, idList)


if __name__ == '__main__':
    main()
