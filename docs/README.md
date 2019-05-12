## Starting phpIPAM for the first time

   1. docker-compose up -d
   1. Wait about 30s to 1m for the systems to initialize
   1. Browse to http://0.0.0.0:8000
   1. login user=admin, password=ipamadmin
   1. You will be prompted for a new password, enter that and don't forget it!
   
## Setup API and new User

   1. Enable API in phpIPAM Settings page
   1. Create an API "app" key with read/write permissions, and security=none   
   1. Create a new user for login purposes; make Administrator
   

## Create sample data

   1. Create a new Section
   1. Create a few Subnets in that section
   1. Create a few Addresses in those subnets
   
   
## Access the API

Look in the `examples` directory and you will some files you can use to get
started with the API.  Make sure the values you define in the 'setup-env.sh' file
match those you used when settings up the phpIPAM system.

Have fun!   