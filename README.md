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

		sudo pip install git+https://github.com/frappe/bench


Basic Usage
===========

* Create a new bench

		bench init erpnext-bench && cd erpnext-bench

* Add apps

		bench get-app erpnext https://github.com/frappe/erpenxt

* Add site

		bench new-site site1.local

* Serve site

		bench frappe --serve


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
