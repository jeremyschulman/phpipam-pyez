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
Set of utility functions to work with the PhpIpamClient instance.
"""

from operator import itemgetter
from collections import Callable
from http import HTTPStatus


__all__ = [
    'create_index',
    'expand_ids'
]


def create_index(list_of_dict, key='id'):
    """
    This function will take a list of dictionaries and use the `key` value to create a dictionary
    of keys whose value is the dict item.  The key can be in one of the following forms:

        str - a single named item in the dictionary; by default 'id'

        tuple - two or more string value that are used ot make the key.

        callable - a user-defined callable function; this function would take as a single
        argument the dictionary item; and return the key value.

    Parameters
    ----------
    list_of_dict : list[dict]
        A list of dictionaries to product the index

    key : str|tuple|callable
        As described above

    Returns
    -------
    dict
        The "index" dictionary as described above.
    """
    if isinstance(key, str):
        get_key = itemgetter(key)
    elif isinstance(key, tuple):
        get_key = itemgetter(*key)
    elif isinstance(key, Callable):
        get_key = key
    else:
        raise ValueError('key is not str|callable')

    return {get_key(item): item for item in list_of_dict}


def expand_ids(controller, list_of_ids):
    """
    This function is used to take a list of API ID values (str) and fetch the
    item data from the API one at a time.  This function returns that list of
    dicts.  If the API returns a 400 response, this function will raise a
    RuntimeError; but that exception will contain the list of processed items up
    to the point of the API failure.

    Parameters
    ----------
    controller : PhpIpamClient controller instance
        The controller instance that will provide the 'get' method
        used to fetch the item data from the API.

    list_of_ids : list[str]
        The list of ID values.

    Examples
    --------
        list_of_dict = expand_ids(client.addresses, list_of_address_ids)

    Returns
    -------
    list[dict]
        The list of dict items fetched from the API.

    Raises
    ------
    RuntimeError
        When the API returns an HTTP 400 response code.  The args included in the
        exception will be:
            args[0] = str: message
            args[1] = list[dict] of items that were processed ok
            args[2] = ID of failed API call
            args[3] = Request response object of failed API call
    """
    found_list = list()

    for each in list_of_ids:
        res = controller.get(each)
        code = res.status_code
        if code == HTTPStatus.BAD_REQUEST:
            raise RuntimeError(f'ERROR processing ID {each}: {res.text}',
                               found_list, each, res)

        res.raise_for_status()
        found_list.append(res.json()['data'])

    return found_list


# TODO: experimental
# def touch(self, **kwargs):
#     """
#     Try to create a dummy item in this section for the purposes of reading back
#     the actual item parameters.  If the item is created, then it will also be
#     immediately removed; but the item body will be returned to caller so
#     they can examine the item parameters.
#
#     Other Parameters
#     ----------------
#     kwargs - used to provide required values when attempting the post
#
#     Returns
#     -------
#     dict
#         The new item body
#     """
#     try:
#         got = self.post(json=kwargs)
#         got.raise_for_status()
#         body = got.json()
#         new_id = body.get('id') or body['data']['id']
#
#     except Exception as exc:
#         raise RuntimeError(exc)
#
#     got = self.get(f"/{new_id}")
#     self.delete(f"/{new_id}")
#     return got.json()['data']


