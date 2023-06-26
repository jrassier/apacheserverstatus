"""Details of an Apache server's /server-status page expressed a bit more conveniently"""

import datetime
import requests
import json
from pprint import pprint
from bs4 import BeautifulSoup
from dateutil import tz, parser


def get_offset(naive_timestamp, utc_equivalent):
    # Positive UTC offset
    if naive_timestamp > utc_equivalent:
        return abs(naive_timestamp - utc_equivalent)
    # Negative UTC offset
    else:
        return abs(utc_equivalent - naive_timestamp)


class ApacheServerStatus:
    debug = False

    slot_modes = {'_': 'waiting', 'S': 'starting_up', 'R': 'reading_request', 'W': 'sending_reply', 'K': 'keepalive',
                  'D': 'dns_lookup', 'C': 'closing_connection', 'L': 'logging', 'G': 'gracefully_finishing',
                  'I': 'idle_cleanup', '.': 'open'}

    @staticmethod
    def write_debug(msg):
        if ApacheServerStatus.debug:
            print(f"{datetime.datetime.now()} ApacheServerStatus {msg}")

    def dump(self):
        pprint(self.__dict__)

    def __init__(self, status_url):
        self.status_url = status_url
        ApacheServerStatus.write_debug(f"Initialized with URL {status_url}")
        self.last_result = None
        self.worker_slots = []
        self.refresh()

    def to_json(self):
        return json.dumps(self.__dict__, sort_keys=True, indent=4)

    def refresh(self):
        http_result = requests.get(self.status_url)
        raw_html = http_result.text
        ApacheServerStatus.write_debug(f"Retrieved {self.status_url} with result {http_result.status_code}")
        http_result.raise_for_status()
        soup = BeautifulSoup(raw_html, 'html.parser')

        # The last two dt tags don't contain a : character so we need to exclude them from this step.
        # There's probably a clever way to do this as a one-liner.
        raw_props = dict(dt.contents[0].strip().split(': ', 1) for dt in (soup.find_all('dt')[:-2]))
        overview = dict((str.lower(k).replace(' ', '_').replace('.', ''), v.strip()) for k, v in raw_props.items())

        # What is working with timestamps without a little time zone fuckery? Apache returns some timezone names, like
        # 'CDT', that Python can't seem to figure out. RFC 2616 14.18 comes to our rescue here, though, because it
        # requires the server to send a UTC Date header with its response. With that header and the value of the
        # 'current time' field in the body, we can work backward to an offset.

        # This is known to be UTC time per RFC
        date_from_resp_header = http_result.headers['date']
        parsed_date_from_resp_header = parser.parse(date_from_resp_header).replace(tzinfo=None)

        # This is in an unknown timezone
        parsed_current_time_from_body = parser.parse(overview['current_time'], ignoretz=True)

        offset = get_offset(parsed_current_time_from_body, parsed_date_from_resp_header)

        self.write_debug(f"Calculated UTC offset: {offset}")

        current_time = parser.parse(overview['current_time'], ignoretz=True) + offset
        current_time = current_time.replace(tzinfo=tz.gettz('UTC'))
        restart_time = parser.parse(overview['restart_time'], ignoretz=True) + offset
        restart_time = restart_time.replace(tzinfo=tz.gettz('UTC'))
        server_built = parser.parse(overview['server_built'], ignoretz=True)
        server_built = server_built.replace(tzinfo=tz.gettz('UTC'))

        # Parse date/time values into objects
        overview['current_time_raw'] = overview['current_time']
        overview['current_time_utc'] = current_time.isoformat()
        overview['current_time_epoch'] = int(current_time.timestamp())
        overview['restart_time_raw'] = overview['restart_time']
        overview['restart_time_utc'] = restart_time.isoformat()
        overview['restart_time_epoch'] = int(current_time.timestamp())
        overview['server_built_raw'] = overview['server_built']
        overview['server_built_utc'] = server_built.isoformat()
        overview['server_built_epoch'] = int(current_time.timestamp())

        del overview['current_time']
        del overview['restart_time']
        del overview['server_built']

        # Break out load figures into L1/L5/L15
        loads = overview['server_load'].split(' ')
        overview['server_load'] = {'L1': loads[0], 'L5': loads[1], 'L15': loads[2]}

        # Separate 'total accesses' and 'total traffic'
        ta = overview['total_accesses'].split('-')
        overview['total_accesses'] = ta[0].strip()
        overview['total_traffic'] = ta[1].split(':')[1].strip()

        self.__dict__ = overview

        # Parse the worker slot table
        self.worker_slots = []

        # Grab the headings from the first row
        headings = [str.lower(h.text.strip()) for h in soup.table.contents[0].contents]

        # Grab the values from all subsequent rows
        for row in soup.select('table')[0].findAll('tr')[1:]:
            worker_slot = dict(zip(headings, [td.text.strip() for td in row.findAll('td')]))
            worker_slot['mode'] = self.slot_modes[worker_slot['m']]
            self.worker_slots.append(worker_slot)
