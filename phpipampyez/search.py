# Copyright 2019 Jeremy Schulman, nwkautomaniac@gmail.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This file contains the code used to execute the "search" tool and return back found items.
"""

import json
from requests.cookies import create_cookie
from bs4 import BeautifulSoup

from phpipampyez.utils import expand_ids


DEFAULT_SEARCH_OPTIONS = [
    'addresses', 'subnets', 'vlans', 'vrf'
]

SEARCH_OPTIONS = DEFAULT_SEARCH_OPTIONS + ['pstn', 'circuits']


def extracto_subnets(soup):
    found = soup.find_all('tr', attrs={'class': 'subnetSearch'})
    return [item.attrs['subnetid'] for item in found]


def extracto_addresses(soup):
    found = soup.find_all('tr', attrs={'class': 'ipSearch'})
    return [item.attrs['id'] for item in found]


def extracto_vlans(soup):
    text = 'Search results (VLANs):'
    anchor = soup.find('h4', text=text)
    if not anchor:
        return []

    table = anchor.find_next_sibling('table')
    items = table.find_all('a', attrs={'data-action': 'edit'})
    return [item['data-vlanid'] for item in items]


def extracto_vrfs(soup):
    text = 'Search results (VRFs):'

    anchor = soup.find('h4', text=text)
    if not anchor:
        return []

    table = anchor.find_next_sibling('table')
    items = table.find_all('a', attrs={'data-action': 'edit'})
    return [item['data-vrfid'] for item in items]


def search(client, find, search_options, expand=False):
    """
    Executes the "search" tool found on the WebUI and returns back structured results.
    See the same method defined in the PhpIpamClient class.
    """

    search_url = client.api.phpipam_host + f'/tools/search/{find}'

    # determine the search options based on whether or not the caller provided
    # them.  If they did not, then use the defaults; i.e. those listed in
    # DEFAULT_SEARCH_OPTIONS.  Options specified will be turned 'on' in the
    # search; 'off' otherwise.

    opt_settings = search_options or DEFAULT_SEARCH_OPTIONS

    opt_dict = {opt: ('off', 'on')[opt in opt_settings]
                for opt in SEARCH_OPTIONS}

    # the search options are specified as a cookie called 'search_parameters';
    # found this by introspecting the WebUI network calls.  The cookie is a
    # dict, so we must dump to JSON for the purpose of HTTP usage.

    client.webui.cookies.set_cookie(create_cookie('search_parameters', json.dumps(opt_dict)))

    # The search is invoked as a HTTP GET call, and then we need to parse the HTML results.
    # using the BeautifulSoup package for this purpose.

    res = client.webui.get(search_url)
    res.raise_for_status()
    soup = BeautifulSoup(res.content, 'html.parser')

    # Store each set of results in separate keys that correspond to the search
    # option keys.  For any option that is either not specified as part of the
    # search, or if the results yield no values, the list will be an empty list
    # ([]), and not `None`.

    results = dict()

    results['subnets'] = extracto_subnets(soup)
    results['addresses'] = extracto_addresses(soup)
    results['vlans'] = extracto_vlans(soup)
    results['vrfs'] = extracto_vrfs(soup)

    # TODO: add pstn and circuits

    # If the caller did not request the ID values to be expanded into data
    # dictionaries, then we are all done, and can return the results now.

    if not expand:
        return results

    # If we are here, then we need to transform the list of IDs to list of dicts

    results['subnets'] = expand_ids(client.subnets, results['subnets'])
    results['addresses'] = expand_ids(client.addresses, results['addresses'])
    results['vlans'] = expand_ids(client.vlans, results['vlans'])
    results['vrfs'] = expand_ids(client.vrfs, results['vrfs'])

    return results
