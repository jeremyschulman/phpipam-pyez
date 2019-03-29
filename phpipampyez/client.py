from operator import itemgetter
from collections import Callable
from requests import Session


device_params = """
parameter	type	methods	description
id	number	GET, PATCH, DELETE	Device identifier
hostname	varchar	POST, PATCH	Device hostname
ip_addr	varchar	POST, PATCH	Device ip address
descriptuion	varchar	POST, PATCH	Device description
sections	varchar	POST, PATCH	List of section id's device belongs to (e.g. 3;4;5)
rack, rack_start, rack_size	varchar	POST, PATCH	Device rack index, start position and size in U
location	varchar	POST, PATCH	Device location index
"""


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

        if isinstance(key, str):
            get_key = itemgetter(key)
        elif isinstance(key, tuple):
            get_key = itemgetter(*key)
        elif isinstance(key, Callable):
            get_key = key
        else:
            raise ValueError('key is not str|callable')

        self.catalog = {get_key(item): item for item in body.get('data', {})}

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
            subsec = phpIPAMSection(client=self.client, section_url=self.base_url + f"/{subsect_name}")
            setattr(self, item, subsec)
            return subsec

        def decorate(url='', **kwargs):
            return getattr(self.api, item)(f"{self.base_url}{url}", **kwargs)
        return decorate


class phpIPAMClient(object):
    """
    Pythonic client for the phpIPAM system.
    """
    def __init__(self, host, user, password, app, port=80):
        """
        Create as new client session and login.

        Parameters
        ----------
        host : str
            The hostname/ipaddr of the phpIPAM server

        user : str
            The login user-name

        password : str
            The login password

        app : str
            The login application name.  An API app must be defined within
            the phpIPAM system to access the API.

        port : str
            The host server port; defaults to 80
        """
        self.api = Session()
        self._api_auth = (user, password)
        self.base_url = f"http://{host}:{port}/api/{app}"
        self.login()

    def login(self):
        got = self.api.post(self.base_url + "/user", auth=self._api_auth)
        got.raise_for_status()
        token = got.json()['data']['token']
        self.api.headers['token'] = token

    def __getattr__(self, item):
        new_sec = phpIPAMSection(self, section_url=f"{self.base_url}/{item}")
        setattr(self, item, new_sec)
        return new_sec
