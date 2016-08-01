Bench
=====

The bench allows you to setup Frappe / ERPNext apps on your local Linux (CentOS 6, Debian 7, Ubuntu, etc) machine or a production server. You can use the bench to serve multiple frappe sites. If you are using a DigitalOcean droplet or any other VPS / Dedicated Server, make sure it has >= 1Gb of ram or has swap setup properly.

To do this install, you must have basic information on how Linux works and should be able to use the command-line. If you are looking easier ways to get started and evaluate ERPNext, [download the Virtual Machine](https://erpnext.com/download) or take [a free trial on erpnext.com](https://erpnext.com/pricing).

If you have questions, please ask them on our [forum](https://discuss.erpnext.com/).

Installation
============

Easy Setup
----------

- This is an opinionated setup with logging and SE Linux. So, it is best to setup on a blank server.
- Tested on Ubuntu 14.04 to 16.04, CentOS 7+, and MacOS X. If you find any problems, post them on our forum: [https://discuss.erpnext.com](https://discuss.erpnext.com)
- This script will install the pre-requisites, install bench and setup an ERPNext site
- Passwords for Frappe Administrator and MariaDB (root) will be asked
- You can then login as **Administrator** with the Administrator password

Production vs Develop
---------------------

*Production* setup should be run on a new box and installs nginx and supervisor to manage the processes. *Develop* setup uses `honcho` to manage the processes and uses the built-in web server (`bench start`)

Steps
-----

Open your Terminal and enter:

	# Linux:

	wget https://raw.githubusercontent.com/frappe/bench/master/playbooks/install.py

	# Mac OSX:

	# install X Code (from App store)
	# install HomeBrew (http://brew.sh/)
	brew install python
	brew install git
	curl "https://raw.githubusercontent.com/frappe/bench/master/playbooks/install.py" -o install.py

	# For development
	sudo python install.py --develop

	# For production
	sudo python install.py --production

	# If you're logged in as root, use --user flag to create a user and install using that user
	sudo python install.py --develop --user frappe


For development, you have to explicitly start services by running `bench start`. This script requires Python2.7+ installed on your machine. You will have to manually create a new site (`bench new-site`) and get apps that you need (`bench get-app`, `bench install-app`).

For production, you will have a preinstalled site with ERPNext installed in it.

You need to run this with a user that is **not** `root`, but can `sudo`. If you don't have such a user, you can search the web for *How to add a new user in { your OS }* and *How to add an existing user to sudoers in { your OS }*.

On Mac OS X, you will have to create a group with the same name as *{ your User }*. On creating this group, you have to assign *{ your User }* to it. You can do this by going to "System preferences" -> "Users & Groups" -> "+" (as if you were adding new account) -> Under "New account" select "Group" -> Type in group name -> "Create group"

This script will:

- Install pre-requisites like git and ansible
- Shallow clones this bench repository under `/usr/local/frappe/bench-repo`
- Runs the Ansible playbook 'playbooks/develop/install.yml', which:
	- Installs
		- MariaDB and its config
		- Redis
		- NodeJS
		- WKHTMLtoPDF with patched QT
	- Initializes a new Bench at `~/frappe/frappe-bench` with `frappe` framework already installed under `apps`.

####Script Options:
```
	--help
	--verbose
	--develop
	--production
	--site
	--user
	--bench-branch
	--repo-url
```

Updating
========

To manually update the bench, run `bench update` to update all the apps, run
patches, build JS and CSS files and restart supervisor (if configured to).

You can also run the parts of the bench selectively.

`bench update --pull` will only pull changes in the apps

`bench update --patch` will only run database migrations in the apps

`bench update --build` will only build JS and CSS files for the bench

`bench update --bench` will only update the bench utility (this project)

`bench update --requirements` will only update dependencies (python packages) for the apps installed


Guides
=======
- [Configuring HTTPS](https://frappe.github.io/frappe/user/en/bench/guides/configuring-https.html)
- [Using Let's Encrypt to setup HTTPS](https://frappe.github.io/frappe/user/en/bench/guides/lets-encrypt-ssl-setup.html)
- [Diagnosing the Scheduler](https://frappe.github.io/frappe/user/en/bench/guides/diagnosing-the-scheduler.html)
- [Change Hostname](https://frappe.github.io/frappe/user/en/bench/guides/how-to-change-host-name-from-localhost.html)
- [Manual Setup](https://frappe.github.io/frappe/user/en/bench/guides/manual-setup.html)
- [Setup Production](https://frappe.github.io/frappe/user/en/bench/guides/setup-production.html)
- [Setup Multitenancy](https://frappe.github.io/frappe/user/en/bench/guides/setup-multitenancy.html)
- [Stopping Production](https://frappe.github.io/frappe/user/en/bench/guides/stop-production-and-start-development.html)


Resources
=======

- [Background Services](https://frappe.github.io/frappe/user/en/bench/resources/background-services.html)
- [Bench Commands Cheat Sheet](https://frappe.github.io/frappe/user/en/bench/resources/bench-commands-cheatsheet.html)
- [Bench Procfile](https://frappe.github.io/frappe/user/en/bench/resources/bench-procfile.html)
