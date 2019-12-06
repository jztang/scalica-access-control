## Scalica Access Control

Large Scale Team 12

- Liran Kogan
- Francisco Pardo
- Ian Tai
- Jason Tang

### First installation

Install required packages:

`$ sudo apt-get update`

`$ sudo apt-get install mysql-server libmysqlclient-dev python-dev python-virtualenv`
(Set a mysql root password)

`$ ./first_install.sh`

Installation for the new tools we're using:

`$ python -m pip install --upgrade pip`

`$ pip install --user redis grpcio grpcio-tools`

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

### File directory overview

![](http://i.imgur.com/PY6ziB9.png)

### Navigating the site

The website lacks the UI to navigate it normally with mouse clicks, so you'll have to modify the URL to get to what you want.

[/micro](http://localhost:8000/micro/) - the homepage

[/micro/stream/1](http://localhost:8000/micro/stream/1/) - the profile of the user with ID=1 (change the number to get others)

[/follow](http://localhost:8000/micro/follow/) - drop-down menu to follow any registered user (including yourself)

### Testing with the Scalica DB

The MySQL server data is local to the machine so you'll have to generate your own posts/users.

If you want to reset the website and wipe your data, from the project root directory:

`$ cd db`

`$ sudo mysql`

`$ DROP DATABASE scalica;`

`$ exit`

`$ sudo ./install_db.sh`

`$ cd ..`

`$ source ./env/bin/activate`

`$ cd web/scalica`

`$ python manage.py migrate`