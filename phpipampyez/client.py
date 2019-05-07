from operator import itemgetter
from collections import Callable
from requests import Session


class phpIPAMSection(object):

    def __init__(self, client, section_url):
        self.base_url = section_url
        self.client = client
        self.api = client.api
        self.catalog = {}

    def get_catalog(self, key='id'):
        got = self.get()
        got.raise_for_status()
        body = got.json()

        self.catalog = self.client.index(list_of_dict=body.get('data', []), key=key)

    def touch(self, **kwargs):
        """
        Try to create a dummy item in this section for the purposes of reading back
        the actual item parameters.  If the item is created, then it will also be
        immediately removed; but the item body will be returned to caller so
        they can examine the item parameters.

        Other Parameters
        ----------------
        kwargs - used to provide required values when attempting the post

        Returns
        -------
        dict
            The new item body
        """
        try:
            got = self.post(json=kwargs)
            got.raise_for_status()
            body = got.json()
            new_id = body.get('id') or body['data']['id']
        except Exception as exc:
            raise RuntimeError(exc)

        got = self.get(f"/{new_id}")
        self.delete(f"/{new_id}")
        return got.json()['data']

    def wipe(self):
        self.get_catalog('id')
        for each_id in self.catalog:
            self.delete(f"/{each_id}")

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
            This will be either the subsection name, for example "_locations", or
            the api method "get"

        Returns
        -------
        phpIPAMSection
            When the item is a subsection

        callable
            When the item is an API method
        """
        if item.startswith('_'):
            subsect_name = item[1:]
            subsec = phpIPAMSection(client=self.client, section_url=self.base_url + f"{subsect_name}/")
            setattr(self, item, subsec)
            return subsec

        def decorate(url='', **kwargs):
            return getattr(self.api, item)(f"{self.base_url}{url}", **kwargs)
        return decorate


class PhpIpamClient(object):
    """
    Pythonic client for the phpIPAM system.
    """
    def __init__(self, host, user, password, app):
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
        """
        self.api = Session()
        self._api_auth = (user, password)
        self.base_url = f"{host}/api/{app}"
        self.login()

    def login(self):
        got = self.api.post(self.base_url + "/user", auth=self._api_auth)
        got.raise_for_status()
        token = got.json()['data']['token']
        self.api.headers['token'] = token

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
        new_sec = phpIPAMSection(self, section_url=f"{self.base_url}/{item}/")
        setattr(self, item, new_sec)
        return new_sec
