#!/bin/env python3


import requests
import re
import csv
from datetime import datetime
from html.parser import HTMLParser

BASE_URL = 'https://www.queenconcerts.com'
STARTING_URL = 'https://www.queenconcerts.com/live/queen.html'


class BaseParser(HTMLParser):
    def __init__(
            self,
            **kwargs
            ):
        self.links = []
        super().__init__(**kwargs)

    def handle_starttag(
            self,
            tag,
            attrs,
            ):
        if tag == 'a':
            attrDict = {attrKey: attrVal for (attrKey, attrVal) in attrs}
            if 'class' in attrDict \
                    and attrDict['class'] == 'list-group-item list-group-item-action':
                self.links.append(attrDict['href'])

class TourParser(HTMLParser):
    def __init__(
            self,
            **kwargs
            ):
        self.events = []
        self.eventTitle = None
        self.eventDate = None
        self.eventBrief = None
        self.is_h1 = False
        self.tourName = None
        super().__init__(**kwargs)

    def handle_starttag(
            self,
            tag,
            attrs,
            ):
        if tag == 'a':
            attrDict = {attrKey: attrVal for (attrKey, attrVal) in attrs}
            if 'href' in attrDict \
                    and eventUrlRegex.match(attrDict['href']):
                self.eventTitle = attrDict['title']
        elif tag == 'h1':
            self.is_h1 = True

    def handle_endtag(
            self,
            tag,
            ):
        if tag == 'a':
            self.eventTitle = None
            self.eventDate = None
            self.eventBrief = None
        elif tag == 'h1':
            self.is_h1 = False

    def handle_data(
            self,
            data,
            ):
        if self.eventTitle:
            matches = eventDataRegex.match(data)
            if matches:
                self.eventDate = datetime(
                        int(matches.group('year')),
                        int(matches.group('month')),
                        int(matches.group('day')),
                        )
                self.eventBrief = matches.group('brief')
                self.events.append({
                    'Tour Name': self.tourName,
                    'title': self.eventTitle,
                    'date': self.eventDate,
                    'brief': self.eventBrief,
                    })
        elif self.is_h1:
            self.tourName = data

eventUrlRegex = re.compile(
        r'/detail/live/\d+/',
        re.IGNORECASE
        )

eventDataRegex = re.compile(
        r'^(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})\s+(?P<brief>.*)$',
        )

def get_response(
        url,
        parser = None,
        ):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
        }
    resp = requests.get(url, headers=headers, timeout=5)
    if resp.ok and parser:
        parser.feed(resp.text)
        return parser
    elif resp.ok:
        return resp.text
    else:
        resp.raise_for_status()

if __name__ == '__main__':
    baseParser = BaseParser()
    tourParser = TourParser()

    parsedBase = get_response(STARTING_URL, baseParser)

    for tourLink in parsedBase.links:
        parsedEvent = get_response(BASE_URL+tourLink, tourParser)

    with open('events.csv', 'w', newline='') as f:
        dictWriter = csv.DictWriter(f, tourParser.events[0].keys())
        dictWriter.writeheader()
        dictWriter.writerows(tourParser.events)
