"""
This file contains the code used to execute the "search" tool and return back found items.
"""
import json
from requests.cookies import create_cookie
from bs4 import BeautifulSoup


def extracto_subnets(client, soup, return_ids):
    found = soup.find_all('tr', attrs={'class': 'subnetSearch'})
    found_ids = [item.attrs['subnetid'] for item in found]

    if return_ids:
        return found_ids

    found_list = list()
    for each in found_ids:
        res = client.subnets.get(each)
        res.raise_for_status()
        found_list.append(res.json()['data'])

    return found_list


def extracto_addresses(client, soup, return_ids):

    found = soup.find_all('tr', attrs={'class': 'ipSearch'})
    found_ids = [item.attrs['id'] for item in found]

    if return_ids:
        return found_ids

    found_list = list()

    for each in found_ids:
        res = client.addresses.get(each)
        res.raise_for_status()
        found_list.append(res.json()['data'])

    return found_list


def extracto_vlans(client, soup, return_ids):
    text = 'Search results (VLANs):'
    anchor = soup.find('h4', text=text)
    if not anchor:
        return []

    table = anchor.find_next_sibling('table')
    items = table.find_all('a', attrs={'data-action': 'edit'})
    found_ids = [item['data-vlanid'] for item in items]

    if return_ids:
        return found_ids

    found_list = list()

    for each in found_ids:
        res = client.vlans.get(each)
        res.raise_for_status()
        found_list.append(res.json()['data'])

    return found_list


def extracto_vrfs(client, soup, return_ids):
    anchor = soup.find('h4', text='Search results (VRFs):')
    if not anchor:
        return []

    table = anchor.find_next_sibling('table')
    items = table.find_all('a', attrs={'data-action': 'edit'})
    found_ids = [item['data-vrfid'] for item in items]

    if return_ids:
        return found_ids

    found_list = list()

    for each in found_ids:
        res = client.vrfs.get(each)
        res.raise_for_status()
        found_list.append(res.json()['data'])

    return found_list


DEFAULT_SEARCH_PARAMS = {
    "addresses": "on",
    "subnets": "on",
    "vlans": "on",
    "vrf": "on",
    "pstn": "off",
    "circuits": "off"
}


def search(client, find, search_options, return_ids):
    """
    Executes the "search" tool found on the WebUI and returns back structured results.
    See the same method defined in the PhpIpamClient class.
    """

    search_url = client.api.phpipam_host + f'/tools/search/{find}'

    sp_dict = dict()
    if search_options:
        for param in DEFAULT_SEARCH_PARAMS:
            sp_dict[param] = 'on' if param in search_options else 'off'
    else:
        sp_dict.update(DEFAULT_SEARCH_PARAMS)

    client.webui.cookies.set_cookie(create_cookie('search_parameters', json.dumps(sp_dict)))
    res = client.webui.get(search_url)
    res.raise_for_status()

    # use bs4 to web scrape the results

    soup = BeautifulSoup(res.content, 'html.parser')

    results = dict()

    results['subnets'] = extracto_subnets(client, soup, return_ids)
    results['addresses'] = extracto_addresses(client, soup, return_ids)
    results['vlans'] = extracto_vlans(client, soup, return_ids)
    results['vrfs'] = extracto_vrfs(client, soup, return_ids)

    # TODO: add pstn and circuits
    return results

