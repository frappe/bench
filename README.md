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

		`sudo pip install git+https://github.com/frappe/bench`


Usage
=====

* Create a new bench
		`bench init erpnext-bench && cd erpnext-bench`

* Add apps
		`bench get-app erpnext https://github.com/frappe/erpenxt`

* Add site
		`bench new-site site1.local`

* Serve site
		`bench frappe --serve`
