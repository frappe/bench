Bench
=====

The bench allows you to setup Frappe / ERPNext apps on your local Linux (CentOS 6, Debian 7, Ubuntu, etc) machine or a production server. You can use the bench to serve multiple frappe sites. If you are using a DigitalOcean droplet or any other VPS / Dedicated Server, make sure it has >= 1Gb of ram or has swap setup properly.

To do this install, you must have basic information on how Linux works and should be able to use the command-line. If you are looking easier ways to get started and evaluate ERPNext, [download the Virtual Machine](https://erpnext.com/download) or take [a free trial on erpnext.com](https://erpnext.com/pricing).

If you have questions, please ask them on our [forum](https://discuss.erpnext.com/).

Installation
============

Production vs Development
--------------------

| Production                                                               | Development                                                       |
|--------------------------------------------------------------------------|-------------------------------------------------------------------|
| The Production setup uses Nginx and Supervisor                           | The development setup uses Socketio.                              |
| This setup isn't meant for instant updates in code.                      | Any code changes will be reflected instantly.                     |
| Background services handle all the work, and they start with the system. | You need to explicitly start your server by running `bench start` |
| Uses Celery for job queuing                                              | Uses RQ for queuing                                               |
| Installs with master branch                                              | Installs with develop branch                                      |


Easy Setup 
---------------------
- This is an opinionated setup with logging and SE Linux. So, it is best to setup on a blank server.
- Supported for CentOS 6, CentOS 7, Debian 7 and Ubuntu 12.04 to 15.x
- This script will install the pre-requisites, install bench and setup an ERPNext site
- Passwords for Frappe, Frappe Administrator and MariaDB (root) will be generated
- You can then login as **Administrator** with the Administrator password printed 

Open your Terminal and enter:


####For Production:
```
wget https://raw.githubusercontent.com/frappe/bench/master/install_scripts/setup_frappe.sh
sudo bash setup_frappe.sh --setup-production
```
This will install Frappe and ERPNext with Supervisor, Nginx and Celery. Supervisor will keep all services working in the background and make sure they all run.

####For Development:
> We recommend using the [Beta Development Setup](#beta-development-setup) if it supports your OS

```
wget https://raw.githubusercontent.com/frappe/bench/master/install_scripts/setup_frappe.sh
sudo bash setup_frappe.sh --bench-branch develop
```
This will install with Socketio and Redis Queue. You have to explicitly start services by running `bench start`.

####Script Options:
```
	-h | --help 
	-v | --verbose 
	--mysql-root-password 
	--frappe-user 
	--setup-production 
	--skip-setup-bench 
	--skip-install-bench 
```


Beta Development Setup
------------------------

Tested on Ubuntu 14.04 to 15.x, Debian 7+, CentOS 7+, and MacOS X. If you find any problems, post them on our forum: [https://discuss.erpnext.com](https://discuss.erpnext.com)

```
Linux: 
wget https://raw.githubusercontent.com/frappe/bench/develop/playbooks/install.py

Mac OSX:
curl "https://raw.githubusercontent.com/frappe/bench/master/playbooks/install.py" -o install.py

python install.py --develop
```
This will install with Socketio and Redis Queue. You have to explicitly start services by running `bench start`. This script requires Python2.7+ installed on your machine. You need to run this with a user that is **not** `root`, but can `sudo`. If you don't have such a user, you can search the web for *How to add a new user in { your OS }* and *How to add an existing user to sudoers in { your OS }*.

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
	
You will have to manually create a new site (`bench new-site`) and get apps that you need (`bench get-app`, `bench install-app`).


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
