## Scalica Access Control

Large Scale Team 12

- Liran Kogan
- Francisco Pardo
- Ian Tai
- Jason Tang

### First installation

Install required packages

`$ sudo apt-get update`

`sudo apt-get install mysql-server libmysqlclient-dev python-dev python-virtualenv`
(Set a mysql root password)

`$ ./first_install.sh`

Install the proper databases

`$ cd db`

`$ ./install_db.sh`
(Will ask for the mysql root password configured above).

`$ cd ..`

Sync the database

`$ source ./env/bin/activate`

`$ cd web/scalica`

`$ python manage.py makemigrations micro`

`$ python manage.py migrate`

### Run the server
From the project root directory:

`$ source ./env/bin/activate`

`$ cd web/scalica`

`$ python manage.py runserver`

Access the site at <http://localhost:8000/micro>
