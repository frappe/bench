
<div align="center">
    <img src="https://github.com/frappe/design/raw/master/logos/png/bench-logo.png" height="128">
    <h2>Frappe Bench</h2>
</div>

[![Build Status](https://circleci.com/gh/frappe/bench.svg?style=svg)](https://circleci.com/gh/frappe/bench)

The bench is a command-line utility that helps you to install apps, manage multiple sites and update Frappe / ERPNext apps on */nix (CentOS, Debian, Ubuntu, etc) for development and production. Bench will also create nginx and supervisor config files, setup backups and much more.

If you are using on a VPS make sure it has >= 1Gb of RAM or has swap setup properly.

To do this install, you must have basic information on how Linux works and should be able to use the command-line. If you are looking easier ways to get started and evaluate ERPNext, [download the Virtual Machine](https://erpnext.com/download) or take [a free trial on erpnext.com](https://erpnext.com/pricing).

If you have questions, please ask them on the [forum](https://discuss.erpnext.com/).

## Installation

### Installation Requirements

You will need a computer/server. Options include:

- A Normal Computer/VPS/Baremetal Server: This is strongly recommended. Frappe/ERPNext installs properly and works well on these
- A Raspberry Pi, SAN Appliance, Network Router, Gaming Console, etc.: Although you may be able to install Frappe/ERPNext on specialized hardware, it is unlikely to work well and will be difficult for us to support. Strongly consider using a normal computer/VPS/baremetal server instead. **We do not support specialized hardware**.
- A Toaster, Car, Firearm, Thermostat, etc.: Yes, many modern devices now have embedded computing capability. We live in interesting times. However, you should not install Frappe/ERPNext on these devices. Instead, install it on a normal computer/VPS/baremetal server. **We do not support installing on noncomputing devices**.

To install the Frappe/ERPNext server software, you will need an operating system on your normal computer which is not Windows. Note that the command line interface does work on Windows, and you can use Frappe/ERPNext from any operating system with a web browser. However, the server software does not run on Windows. It does run on other operating systems, so choose one of these instead:

- Linux: Debian, Ubuntu, CentOS are the preferred distros and are well tested. [Arch Linux](https://github.com/frappe/bench/wiki/Install-ERPNext-on-ArchLinux) can also be used
- Mac OS X

### Manual Install

To manually install frappe/erpnext, you can follow this [this wiki](https://github.com/frappe/frappe/wiki/The-Hitchhiker%27s-Guide-to-Installing-Frappe-on-Linux) for Linux and [this wiki](https://github.com/frappe/frappe/wiki/The-Hitchhiker's-Guide-to-Installing-Frappe-on-Mac-OS-X) for MacOS. It gives an excellent explanation about the stack. You can also follow the steps mentioned below:

#### 1. Install Pre-requisites
<pre>
• Python 3.6+
• Node.js 12
• Redis 5					(caching and realtime updates)
• MariaDB 10.3 / Postgres 9.5			(to run database driven apps)
• yarn 1.12+					(js dependency manager)
• pip 15+					(py dependency manager)
• cron 						(scheduled jobs)
• wkhtmltopdf (version 0.12.5 with patched qt) 	(for pdf generation)
• Nginx 					(for production)						
</pre>
#### 2. Install Bench

Install bench as a *non root* user,

	git clone https://github.com/frappe/bench bench-repo
	pip install --user -e bench-repo

Note: Please do not remove the bench directory the above commands will create

#### Basic Usage

* Create a new bench

	The init command will create a bench directory with frappe framework
	installed. It will be setup for periodic backups and auto updates once
	a day.

		bench init frappe-bench && cd frappe-bench

* Add a site

	Frappe apps are run by frappe sites and you will have to create at least one
	site. The new-site command allows you to do that.

		bench new-site site1.local

* Add apps

	The get-app command gets remote frappe apps from a remote git repository and installs them. Example: [erpnext](https://github.com/frappe/erpnext)

		bench get-app erpnext https://github.com/frappe/erpnext

* Install apps

	To install an app on your new site, use the bench `install-app` command.

		bench --site site1.local install-app erpnext

* Start bench

	To start using the bench, use the `bench start` command

		bench start

	To login to Frappe / ERPNext, open your browser and go to `[your-external-ip]:8000`, probably `localhost:8000`

	The default username is "Administrator" and password is what you set when you created the new site.


---

## Easy Install

- This is an opinionated setup so it is best to setup on a blank server.
- Works on Ubuntu 16.04+, CentOS 7+, Debian 8+
- You may have to install Python 2.7 (eg on Ubuntu 16.04+) by running `apt-get install python-minimal`
- You may also have to install build-essential and python-setuptools by running `apt-get install build-essential python-setuptools`
- This script will install the pre-requisites, install bench and setup an ERPNext site
- Passwords for Frappe Administrator and MariaDB (root) will be asked
- MariaDB (root) password may be `password` on a fresh server
- You can then login as **Administrator** with the Administrator password
- If you find any problems, post them on the forum: [https://discuss.erpnext.com](https://discuss.erpnext.com)

Open your Terminal and enter:

#### 1. Download the install script

For Linux:

	wget https://raw.githubusercontent.com/frappe/bench/master/playbooks/install.py


#### 2. Run the install script

If you are on a fresh server and logged in as root, at first create a dedicated user for frappe
& equip this user with sudo privileges

```
  adduser [frappe-user]
  usermod -aG sudo [frappe-user]
```

*(it is very common to use "frappe" as frappe-username, but this comes with the security flaw of ["frappe" ranking very high](https://www.reddit.com/r/dataisbeautiful/comments/b3sirt/i_deployed_over_a_dozen_cyber_honeypots_all_over/?st=JTJ0SC0Q&sh=76e05240) in as a username challenged in hacking attempts. So, for production sites it is highly recommended to use a custom username harder to guess)*

For developer setup:

	sudo python install.py --develop

For production:

	sudo python install.py --production --user [frappe-user]

use --user flag to create a user and install using that user (By default, the script will create a user with the username `frappe` if the --user flag is not used)

	python install.py --develop --user [frappe-user]

use --container flag to install inside a container (this will prevent the `/proc/sys/vm/swappiness: Read-only` file system error)

	sudo python install.py --production --user [frappe-user] --container

use --version flag to install specific version

	python install.py --develop --version 11 --user [frappe-user]

use --python flag to specify virtual environments python version, by default script setup python 3

	python install.py --develop --version 11 --python python2.7 --user [frappe-user]

#### What will this script do?

- Install all the pre-requisites
- Install the command line `bench`
- Create a new bench (a folder that will contain your entire frappe/erpnext setup)
- Create a new ERPNext site on the bench

#### How do I start ERPNext

1. For development: Go to your bench folder (`frappe-bench` by default) and start the bench with `bench start`
2. For production: Your process will be setup and managed by `nginx` and `supervisor`. [Setup Production](https://frappe.io/docs/user/en/bench/guides/setup-production.html)

---


## Bench Manager (GUI for Bench)

Bench Manager is a graphical user interface to emulate the functionalities of Frappé Bench. Like the command line utility it helps you install apps, manage multiple sites, update apps and much more.

### Installation

```
$ bench setup manager
```

What all it does:
1. Create new site bench-manager.local
2. Gets the `bench_manager` app from https://github.com/frappe/bench_manager if it doesn't exist already
3. Installs the bench_manager app on the site bench-manager.local

## Docker Install - For Developers (beta)

1. For developer setup, you can also use the official [Frappé Docker](https://github.com/frappe/frappe_docker/).
2. The app, mariadb and redis run on individual containers
3. This setup supports multi-tenancy and exposes the frappe-bench volume as a external storage.
4. For more details, [read the instructions on the Frappé Docker README](https://github.com/frappe/frappe_docker/)

Help
====

For bench help, you can type

	bench --help

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
- [Configuring HTTPS](https://frappe.io/docs/user/en/bench/guides/configuring-https.html)
- [Using Let's Encrypt to setup HTTPS](https://frappe.io/docs/user/en/bench/guides/lets-encrypt-ssl-setup.html)
- [Diagnosing the Scheduler](https://frappe.io/docs/user/en/bench/guides/diagnosing-the-scheduler.html)
- [Change Hostname](https://frappe.io/docs/user/en/bench/guides/adding-custom-domains)
- [Manual Setup](https://frappe.io/docs/user/en/bench/guides/manual-setup.html)
- [Setup Production](https://frappe.io/docs/user/en/bench/guides/setup-production.html)
- [Setup Multitenancy](https://frappe.io/docs/user/en/bench/guides/setup-multitenancy.html)
- [Stopping Production](https://github.com/frappe/bench/wiki/Stopping-Production-and-starting-Development)


Resources
=======

- [Background Services](https://frappe.io/docs/user/en/bench/resources/background-services.html)
- [Bench Commands Cheat Sheet](https://frappe.io/docs/user/en/bench/resources/bench-commands-cheatsheet.html)
- [Bench Procfile](https://frappe.io/docs/user/en/bench/resources/bench-procfile.html)
