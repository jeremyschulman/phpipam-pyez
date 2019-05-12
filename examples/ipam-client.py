import os
from phpipampyez import PhpIpamClient

client = PhpIpamClient(host=os.environ['PHPIPAM_HOST'],
                       user=os.environ['PHPIPAM_USER'],
                       password=os.environ['PHPIPAM_PASSWORD'],
                       app=os.environ['PHPIPAM_APIAPP'])
