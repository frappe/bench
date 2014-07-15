Bench
=====

The bench allows you to setup Frappe apps on your local machine or a production
server. You can use the bench to serve multi tenant frappe sites.

Installation
============

Easy way
--------

Supported for CentOS 6, Debian 7 and Ubuntu 12.04+

`curl https://https://raw.githubusercontent.com/frappe/bench/master/install_scripts/setup_frappe.sh | bash`

This script should install the pre-requisites and add a bench command.


Hard Way
--------

Install pre-requisites,

* Python 2.7
* MariaDB
* Redis
	
Install bench,

		git clone https://github.com/frappe/bench
		sudo pip install -e bench

Note: Please do not remove the bench directory the above commands will create


Basic Usage
===========

* Create a new bench

	The init command will create a bench directory with frappe frameowork
	installed. It will be setup for periodic backups and auto updates once
	a day.

		bench init erpnext-bench && cd erpnext-bench

* Add apps

	The get-app command gets and installs frappe apps. Examples include
	(erpnext)[https://github.com/frappe/erpnext] and
	(shopping-cart)[https://github.com/frappe/shopping-cart]

		bench get-app erpnext https://github.com/frappe/erpnext

* Add site

	Frappe apps are run by frappe sites and you will have to create at least one
	site. The new-site command allows you to do that.

		bench new-site site1.local

* Start bench

	To start using the bench, use the `bench start` command

		bench start


Production Deployment
=====================


You can setup the bench for production use by configuring two programs,
Supervisor and nginx.

Supervisor
----------

Supervisor makes sure that the process that power the Frappe system keep running
and it restarts them if they happen to crash. You can generate the required
configuration for supervisor using the command `bench setup supervisor`. The
configuration will be available in `config/supervisor.conf` directory. You can
then copy/link this file to the supervisor config directory and reload it for it to
take effect.

eg,
	
```
bench setup supervisor
sudo ln -s `pwd`/config/supervisor.conf /etc/supervisor/conf.d/frappe.conf
```

The bench will also need to restart the processes managed by supervisor when you
update the apps. To automate this, you will have to setup sudoers using the
command

`bench setup sudoers`

Nginx
-----

Nginx is a web server and we use it to serve static files and proxy rest of the
requests to frappe. You can generate the required configuration for nginx using
the command `bench setup nginx`. The configuration will be available in
`config/nginx.conf` file. You can then copy/link this file to the nginx config
directory and reload it for it to take effect.

eg,

```
bench setup supervisor
sudo ln -s `pwd`/config/nginx.conf /etc/nginx/conf.d/frappe.conf
```
