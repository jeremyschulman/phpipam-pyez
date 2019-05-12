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
This file contains the Pythonic client for the phpIPAM software project.

   * Home: https://phpipam.net/
   * API documentation: https://phpipam.net/api/api_documentation/

"""

from http import HTTPStatus
from requests import Session
from functools import wraps

from phpipampyez import search


__all__ = ['PhpIpamClient']


class PhpIpamClient(object):
    """
    Python client to access phpIPAM system.

    Notes
    -----
    Before use, you must have setup an "app" in the Administration/API panel.
    """

    def __init__(self, host, user, password, app, skip_login=False):
        """
        Create as new client session and login.

        Parameters
        ----------
        host : str
            The host URL to the phpIPAM server, for example "http://my-phpIPAM:8080"

        user : str
            The login user-name

        password : str
            The login password

        app : str
            The login application name.  An API app *MUST* be defined within
            the phpIPAM system to access the API.

        skip_login : bool (optional)
            If set to `True` then do not attempt to login to phpIPAM.
            The default action is login.
        """
        self.api = _PhpIpamApiSession(host=host, app=app)
        self.webui = Session()

        if skip_login is False:
            self.login(user, password)

    def login(self, user, password):
        """
        Login to the phpIPAM system.  When the login is OK, both the client `api` and
        the client `webui` Request session instances can be uses.

        Parameters
        ----------
        user : str - the login user-name
        password : str - the login password

        Raises
        ------
        RuntimeError - denotes an invalid user/password
        HTTPError - any other HTTP response error that is not an "invalid user/password"
        """
        # ---------------------------------------
        # REST API login
        # ---------------------------------------

        res = self.api.post("/user/", auth=(user, password))

        # if res.status_code == 500 and 'Invalid username or password' in res.text:
        #     raise RuntimeError("Login failed: invalid user name or password")

        res.raise_for_status()
        token = res.json()['data']['token']
        self.api.headers['token'] = token

        # ---------------------------------------
        # WebUI login
        # ---------------------------------------

        # we also want to "login" via the WebUI so that we can utilize the tools
        # search feature; not currently available as part of the API proper.

        webui_login = self.api.phpipam_host + '/app/login/login_check.php'
        res = self.webui.post(webui_login, data=dict(ipamusername=user,
                                                     ipampassword=password))
        res.raise_for_status()

        # We do not need to check the actual results body contents.  If the
        # user/password values were not valid, then the previous REST API login
        # will have failed.

    def __getattr__(self, item):
        """
        Returns API controller instance.

        Examples
        --------
        Assume your client variable is called "client".  You could then obtain the
        instance to the "devices" controller by doing this by using "client.devices".
        And from there, you can invoke any requests method, for example:

            res = client.devices.get(...)
            if res.status_code == 200:
                ....

        Parameters
        ----------
        item : str
            The name of the controller, for example "devices".

        Returns
        -------
        _PhpIpamController instance
        """
        if item in self.__dict__:
            return self.__dict__[item]

        new_sec = _PhpIpamController(self, section_url=f"/{item}/")
        setattr(self, item, new_sec)
        return new_sec

    def search(self, find, expand=False, **search_options):
        """
        Perform the same search as found in the WebUI.  This function
        will return a dict[list] structure as described below.

        Parameters
        ----------
        find : str
            The string expression used for search purpose.

        expand : bool
            When True, this function will use the IDs to obtain the full data dict
            for each item.  Note that this could cause a lot of API calls depending
            on the size of the results.

            When False the return lists contain only the ID values.

        Other Parameters
        ----------------
        search_options defines which options to include in the search.  The key
        values are defined by SEARCH_OPTIONS and the default settings are
        defined by DEFAULT_SEARCH_OPTIONS.

        Examples
        --------
        Search only VLANS using "Prod":

            results = client.search("Prod", vlans=True)

        Search Subnets and addresses for "10.113.29"

            results = client.search("10.113.29", subnets=True, addresses=True)

        Search for "MySearchValue" in using the DEFAULT_SEARCH_OPTIONS settings.

            results = client.search("MySearchValue")

        Search of "10.113.29.210" in addresses, and expand the found ID to the actual
        data dict.

            results = client.search("10.113.29.210", addresses=True, expand=True)

        Returns
        -------
        dict[list]
            Keys are defined by `search.SEARCH_OPTIONS`.  Each key contains a
            list of items; either just the IDs or a list[dict] depending on the
            `expand` parameter.
        """
        return search.search(self, find, search_options=search_options, expand=expand)


# -----------------------------------------------------------------------------
#                Internal class definitions used by PhpIpamClient
# -----------------------------------------------------------------------------

class _PhpIpamApiSession(Session):
    """
    Define a requests.Session class for prefixing the phpIPAM server API URL.
    Used by the PhpIpamClient upon instance creation.
    """
    def __init__(self, host, app):
        super(_PhpIpamApiSession, self).__init__()
        self.phpipam_host = host
        self.phpipam_app = app
        self.phpipam_url = f'{host}/api/{app}'

    def prepare_request(self, request):
        request.url = self.phpipam_url + request.url
        return super(_PhpIpamApiSession, self).prepare_request(request)


class _PhpIpamController(object):
    """
    Used to access a phpIpam 'controller'.   Used  by the PhpIpamClient when the
    caller wants to access an API controller area.

    Notes
    -----
    See https://phpipam.net/#controllers
    """

    def __init__(self, client, section_url):
        self.url = section_url
        self.client = client
        self.api = client.api

    def __repr__(self):
        return f'phpIPAM controller API url: {self.url}'

    def __getattr__(self, item):
        """
        meta attribute that returns allows the caller to either
            (1) return a sub-section if the item starts with an underscore (_)
                for example client.tools._locations will return a new instance
                of phpIPAMSection wrapping "locations"

            (2) calls an API method on the calling object, for example, do a POST
                on device with id=1, and json payload ...
                client.devices.post("1", json={}),

        Parameters
        ----------
        item : str
            (a) This will be either the subsection name, for example "_locations", or
            (b) the api method, for example "get"

        Returns
        -------
        _PhpIpamController
            When the item is a subsection

        callable
            When the item is an API method
        """

        # if the item starts with an underscore then we are creating a
        # subsection controller object

        if item.startswith('_'):
            subsect_name = item[1:]
            if item in self.__dict__:
                return self.__dict__[item]

            subsec = _PhpIpamController(client=self.client, section_url=self.url + f"{subsect_name}/")
            setattr(self, item, subsec)
            return subsec

        # if we are here, then item is the name of the `requests` method that we
        # want to invoke, for example "get".

        api_func = getattr(self.api, item)

        @wraps(api_func)
        def decorate(url='', **kwargs):
            return api_func(f"{self.url}{url}/", **kwargs)

        return decorate
