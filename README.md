# phpipam-pyez

Python client for phpIPAM system

# About

As a network automation engineer working at a company that uses [phpIPAM](https://phpipam.net/), I want to be able to access 
the system [API](https://phpipam.net/api/api_documentation/) using the Python programming language.

# Installation

This package is not currently in PyPi.  Therefore you will need to git clone the repository
and then install from your shell:

```bash
python setup.py install
```

# Quick Start

Presuming you have a phpIPAM system running and configured with API access you can
create a client and login to the system using the following as an example.  In this
example, the required initialization values are being taken from environment variables.

Of note, the `host` option needs to be the URL to the phpIPAM server, for example `http://my-ipam-server`


```python
import os
from phpipampyez import PhpIpamClient

client = PhpIpamClient(host=os.environ['PHPIPAM_HOST'],
                       user=os.environ['PHPIPAM_USER'],
                       password=os.environ['PHPIPAM_PASSWORD'],
                       app=os.environ['PHPIPAM_APIAPP'])
```

Once you have the client logged in, you can begin to use any API controller by
attribute access.  For example, the following would invoke the API using the "devices"
controller to retrieve all entries.  Each client controller can be treated like a
`requests` instance providing the HTTP command methods like _get()_, _post()_, etc. 

````python
res = client.devices.get()        # res is a requests response object
res.raise_for_status()
body = res.json()
data = body['data']

for dev_dict in data:
    print(json.dumps(dev_dict)
````

# Setup a local phpIPAM dev-test server

If you want to setup a local phpIPAM server on your laptop for dev-test purposes, there are 
instructions provided in the [docs](docs) directory.

# Enjoy!
