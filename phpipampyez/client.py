"""
This file contains the Pythonic client for the phpIPAM software project.

   * Home: https://phpipam.net/
   * API documentation: https://phpipam.net/api/api_documentation/


Examples
--------
    res = client.addresses.get('search/172.30.35.1/')
    body = res.json()['data']


"""

from operator import itemgetter
from collections import Callable
from requests import Session
from functools import wraps

from phpipampyez.search import search
from phpipampyez.search import DEFAULT_SEARCH_PARAMS


__all__ = ['PhpIpamClient', 'DEFAULT_SEARCH_PARAMS']


class _PhpIpamApiSession(Session):
    """
    Define a requests.Session class for prefixing the phpIPAM server API URL.  Used
    by the PhpIpamClient upon instance creation.
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
    Used to access a phpIPAM 'controller'.   Used  by the PhpIpamClient when the
    caller wants to access an API controller area.

    Notes
    -----
    See https://phpipam.net/#controllers
    """

    def __init__(self, client, section_url):
        self.url = section_url
        self.client = client
        self.api = client.api
        self.catalog = {}

    def __repr__(self):
        return f'phpIPAM controller API url: {self.url}'

    def get_catalog(self, key='id'):
        got = self.get()
        got.raise_for_status()
        body = got.json()

        self.catalog = self.client.index(list_of_dict=body.get('data', []), key=key)

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

    # TODO: experimental
    # def wipe(self):
    #     self.get_catalog('id')
    #     for each_id in self.catalog:
    #         self.delete(f"/{each_id}")

    def __getitem__(self, item):
        return self.catalog.get(item)

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
            The login application name.  An API app must be defined within
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

        got = self.api.post("/user/", auth=(user, password))
        got.raise_for_status()
        token = got.json()['data']['token']
        self.api.headers['token'] = token

        # we also want to "login" via the WebUI so that we can utilize the tools
        # search feature; not currently available as part of the API proper.

        webui_login = self.api.phpipam_host + '/app/login/login_check.php'
        res = self.webui.post(webui_login, data=dict(ipamusername=user,
                                                     ipampassword=password))
        res.raise_for_status()

    @staticmethod
    def index(list_of_dict, key='id'):
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

        """
        if item in self.__dict__:
            return self.__dict__[item]

        new_sec = _PhpIpamController(self, section_url=f"/{item}/")
        setattr(self, item, new_sec)
        return new_sec

    def search(self, find, return_ids=True, **search_options):
        """
        Perform the same search as found in the WebUI.

        Parameters
        ----------
        find : str - the string used for search purpose

        return_ids : bool
            When True the return lists contain only the ID values

            When False, this function will use the IDs to obtain the full data dict
            for each item.  Note that this could cause a lot of API calls depending
            on the size of the results.

        Other Parameters
        ----------------
        search_options defines which options to include in the search.  If not specified
        then the options default to `DEFAULT_SEARCH_PARAMS'

        Returns
        -------
        dict of search results that has the same keys as in
        DEFAULT_SEARCH_PARAMS.  Each key contains a list of items; either just
        the IDs or a list[dict] depending on the `return_ids` parameter.
        """
        return search(self, find, return_ids=return_ids, search_options=search_options)
