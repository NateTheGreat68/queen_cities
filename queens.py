#!/usr/bin/env python3


import requests
import re
import csv
from datetime import datetime
from html.parser import HTMLParser
from typing import Optional, Union

BASE_URL = 'https://www.queenconcerts.com'
STARTING_URL = BASE_URL+'/live/queen.html'


class BaseParser(HTMLParser):
    """
    Parses the page which lists all the tours.

    Members:
      - links: A list of urls for the found tours.

    Init Parameters: Same as the base HTMLParser class.
    """

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
        """
        Looks for tour links by tag name and attributes.
        When a link is found, adds it to the class's "links" member.

        Parameters: Same as the base HTMLParser class's handle_starttag method.
        """
        if tag == 'a':
            attrDict = {attrKey: attrVal for (attrKey, attrVal) in attrs}
            if 'class' in attrDict \
                    and attrDict['class'] == 'list-group-item list-group-item-action':
                self.links.append(attrDict['href'])


class TourParser(HTMLParser):
    """
    Parses a tour page to get a list of events.

    Members:
      - events: A list of the tour's events; each element is a dict with:
        - Tour Name
        - Event Title
        - Event Date
        - Event Venue
        - Event City
      - tourName: The name of the tour.

    Init Parameters: Same as the base HTML Parser class.
    """

    _eventUrlRegex = re.compile(
            r'^/detail/live/\d+/',
            re.IGNORECASE
            )
    _eventDataRegex = re.compile(
            r'^(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})\s+(?P<brief>.*)$',
            )
    _detailsRegex = re.compile(
            r' live at the (?P<venue>[^,]+),\s*(?P<city>.*?(?=\s+\()|.*$)',
            re.IGNORECASE
            )
    _cleanupRegex = re.compile(
            r'^(Queen on tour:\s+|Concert:\s+)',
            re.IGNORECASE
            )

    def __init__(
            self,
            **kwargs
            ):
        self.tourName = None
        self.events = []
        self._eventTitle = None
        self._is_h1 = False

        super().__init__(**kwargs)

    def handle_starttag(
            self,
            tag,
            attrs,
            ):
        """
        Looks for events by tag name and attributes.

        Parameters: Same as the base HTMLParser class's handle_starttag method.
        """
        # Look for an "a" tag with an href attr which matches the given regex.
        # The title of that tag is the event's title, and its data will contain
        # addtional event data.
        if tag == 'a':
            attrDict = {attrKey: attrVal for (attrKey, attrVal) in attrs}
            if 'href' in attrDict \
                    and self._eventUrlRegex.match(attrDict['href']):
                self._eventTitle = attrDict['title']
        # Look for an "h1" tag; this will have the tour name within its data.
        elif tag == 'h1':
            self._is_h1 = True

    def handle_endtag(
            self,
            tag,
            ):
        """
        Resets the members as appropriate so that the next tag from this response
        or the next response can be parsed.

        Parameters: Same as the base HTMLParser class's end_starttag method.
        """
        if tag == 'a':
            self._eventTitle = None
        elif tag == 'h1':
            self._is_h1 = False

    def handle_data(
            self,
            data,
            ):
        """
        Builds information about a tour event from data parsed out of the response.
        Found data is stored in the class's "events" and/or "tourName" members.

        Parameters: Same as the base HTMLParser class's handle_data method.
        """
        # If the _eventTitle member is not None, then that means an event tag
        # is currently being parsed.
        if self._eventTitle:
            eventDataMatches = self._eventDataRegex.search(data)
            detailsMatches = self._detailsRegex.search(self._eventTitle)
            if eventDataMatches:
                self.events.append({
                    'Tour Name': self._cleanupRegex.sub('', self.tourName),
                    'Event Title': self._cleanupRegex.sub('', self._eventTitle),
                    'Event Date': datetime(
                        int(eventDataMatches.group('year')),
                        int(eventDataMatches.group('month')),
                        int(eventDataMatches.group('day')),
                        ),
                    'Event Brief': eventDataMatches.group('brief'),
                    'Event Venue': detailsMatches.group('venue') if detailsMatches else '',
                    'Event City': detailsMatches.group('city') if detailsMatches else '',
                    })
        # If the _is_h1 member is True, then that means the tour name tag is 
        # currently being parsed.
        elif self._is_h1:
            self.tourName = data


def get_response(
        url: str,
        parser: Optional[HTMLParser] = None,
        ) -> Union[HTMLParser, str]:
    """
    Gets an http response from the specified URL and, if applicable, parses it.

    Parameters:
      - url: The url to request.
      - parser: Optional. The parser to feed the request to (and return).
    Return: If a parser is passed, the response will be fed to it and the parser
    will be returned. Otherwise, the text of the response is returned. An
    applicable exception is raised if the response's status isn't OK.
    """
    # The useragent must be specified to get a response from many http servers.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
        }
    resp = requests.get(url, headers=headers, timeout=5)
    if resp.ok and parser: #Response OK and parser passed
        parser.feed(resp.text)
        return parser
    elif resp.ok: #Response OK; no parser passed
        return resp.text
    else: #Response not OK
        resp.raise_for_status()


if __name__ == '__main__':
    """
    Makes an http request for the base URL which lists all the tour (and
    parses the response), then requests and parses the URL for each identified
    tour to get a list of events. The results are written into a csv file.
    """

    baseParser = BaseParser()
    tourParser = TourParser()

    # Get the list of tours.
    parsedBase = get_response(STARTING_URL, baseParser)

    # For each tour, parse the applicable info.
    for tourLink in parsedBase.links:
        parsedEvent = get_response(BASE_URL+tourLink, tourParser)

    # Write the results to a csv file.
    with open('events.csv', 'w', newline='') as f:
        # tourParser's events member is a list of dicts; the dict keys should be
        # the csv headers.
        dictWriter = csv.DictWriter(f, tourParser.events[0].keys())
        dictWriter.writeheader()
        dictWriter.writerows(tourParser.events)
