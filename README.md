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
* wkhtmltopdf (optional, required for pdf generation)
	
Install bench,

		git clone https://github.com/frappe/bench
		sudo pip install -e bench

Note: Please do not remove the bench directory the above commands will create


Basic Usage
===========

* Create a new bench

	The init command will create a bench directory with frappe framework
	installed. It will be setup for periodic backups and auto updates once
	a day.

		bench init erpnext-bench && cd erpnext-bench

* Add apps

	The get-app command fetches and installs frappe apps. Examples include
	(erpnext)[https://github.com/frappe/erpnext] and
	(shopping-cart)[https://github.com/frappe/shopping-cart]

		bench get-app erpnext https://github.com/frappe/erpnext

* Add site

	Frappe apps are run by frappe sites and you will have to create at least one
	site. The new-site command allows you to do just that.

		bench new-site site1.local

* Start bench

	To start using the bench, use the `bench start` command

		bench start


Updating
========

On initializing a new bench, a cronjob is added to automatically update the bench
at 1000hrs (as per the time on your machine). You can disable this by running
`bench config auto_update off` and run `bench config auto_update on` to switch
it on again. To change the time of update, you will have to edit the cronjob
manually using `crontab -e`.

To manually update the bench, run `bench update` to update all the apps, run
patches, build JS and CSS files and restart supervisor (if configured to).

You can also run the parts of the bench selectively.

`bench update --pull` will only pull changes in the apps

`bench update --patch` will only run database migrations in the apps

`bench update --build` will only build JS and CSS files for the bench

`bench update --bench` will only update the bench utility (this project)

Running the bench
==================

To run the bench,

*For development*: `bench start`

*For production*: Configure supervisor and nginx

To run the bench, a few services need to be running apart from the processes.

External services
-----------------

	* MariaDB (Datastore for frappe)
	* Redis (Broker for frappe background workers)
	* nginx (for production deployment)
	* supervisor (for production deployment)

Frappe Processes
----------------

* WSGI Server

	* The WSGI server is responsible for responding to the HTTP requests to
	frappe. In development scenario (`frappe --serve` or `bench start`), the
	Werkzeug WSGI server is used and in production, gunicorn (automatically
	configured in supervisor) is used.

* Celery Worker Processes

	* The Celery worker processes execute background jobs in the Frappe system.
	These processes are automatically started when `bench start` is run and
	for production are configured in supervisor configuration.

* Celery Worker Beat Process

	* The Celery worker beat process schedules enqeueing of scheduled jobs in the
	Frappe system. This process is automatically started when `bench start` is
	run and for production are configured in supervisor configuration.


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
command, `sudo bench setup sudoers`.

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

Note: When you restart nginx after a configuration change, it might fail if
you have another configuration with server block as default for port 80 (in most
cases for the nginx welcome page). You will have to disable this config.  Most
probable places for it to exist are `/etc/nginx/conf.d/default.conf` and
`/etc/nginx/conf.d/default`.
