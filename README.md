<div align="center">
	<img src="https://github.com/frappe/design/raw/master/logos/png/bench-logo.png" height="128">
	<h2>bench</h2>
</div>

bench is a command-line utility that helps you to install apps, manage multiple sites and update Frappe / ERPNext apps on */nix (macOS, Ubuntu, Debian, CentOS, etc) for development and production.


> **Note**: If you are looking for easier ways to get started and evaluate ERPNext, [download the Virtual Machine](https://erpnext.com/download) or take [a free trial on erpnext.com](https://erpnext.com/pricing).

---

# Table of Contents

 - [bench CLI](#bench-cli)
	- [Usage](#usage)
	- [Installation](#installation)
	- [Custom Bench commands](#custom-bench-commands)
 - [Easy Install Script](#easy-install-script)
 - [Release Bench](#release-bench)
 - [Guides](#guides)
 - [Resources](#resources)
 - [License](#license)
---

# bench CLI

Bench is a command line tool that helps you install, setup, manage multiple sites and apps based on Frappe Framework.

---

## Usage

* Create a new bench

		bench init [bench-name]

* Add a site under current bench

		bench new-site [site-name]

	**Optional**: If the database for the site does not reside on localhost or listens on a custom port, you can use the flags `--db-host` to set a custom host and/or `--db-port` to set a custom port.

		bench new-site [site-name] --db-host [custom-db-host-ip] --db-port [custom-db-port]

* Add apps to bench

		bench get-app [app-name] [app-link]

* Install apps on a particular site

		bench --site [site-name] install-app [app-name]

* Start bench (only for development)

		bench start

* Show bench help

		bench --help

_Note:_ Apart from `bench init`, all other bench commands have to be run having the respective bench directory as the working directory. _(`bench update` may also be run, but it's behaviour is covered in depth in the docs)_

For more in depth information on commands and usage follow [here](https://github.com/frappe/bench/blob/master/docs/commands_and_usage.md). As for a consolidated list of bench commands, go through [this page](https://github.com/frappe/bench/blob/master/docs/bench_usage.md).

---

## Installation

To do this install, you must have basic information on how Linux works and should be able to use the command-line. bench will also create nginx and supervisor config files, setup backups and much more. If you are using on a VPS make sure it has >= 1Gb of RAM or has swap setup properly.

	git clone https://github.com/frappe/bench ~/.bench
	pip3 install --user -e ~/.bench

As bench is a python application, its installation really depends on `python` + `pip` + `git`. The Frappe Framework, however has various other system dependencies like `nodejs`, `yarn`, `redis` and a database system like `mariadb` or `postgres`. Go through the [installation requirements](https://github.com/frappe/bench/blob/master/docs/installation.md) for an updated list.

If you have questions, please ask them on the [forum](https://discuss.erpnext.com/c/bench) under the "Install / Update" category.

---

## Custom Bench Commands

Want to utilize a bench command you've added in your custom Frappe application? [This](https://github.com/frappe/bench/blob/master/docs/bench_custom_cmd.md) guide might be of some help.

---

# Easy Install Script

- This is an opinionated setup so it is best to setup on a blank server.
- Works on Ubuntu 16.04+, CentOS 7+, Debian 8+
- You may have to install Python 3 and other essentials by running `apt-get install python3-minimal build-essential python3-setuptools`
- This script will install the pre-requisites, install bench and setup an ERPNext site `(site1.local under frappe-bench)`
- Passwords for Frappe Administrator and MariaDB (root) will be asked and saved under `~/passwoords.txt`
- MariaDB (root) password may be `password` on a fresh server
- You can then login as **Administrator** with the Administrator password
- The log file is saved under `/tmp/logs/install_bench.log` in case you run into any issues during the install.
- If you find any problems, post them on the forum: [https://discuss.erpnext.com](https://discuss.erpnext.com/c/bench) with the `installation_problem` under "Install / Update" category.

		wget https://raw.githubusercontent.com/frappe/bench/master/playbooks/install.py
		python3 install.py --production

Follow [Easy Install Docs](https://github.com/frappe/bench/blob/master/docs/easy_install.md) for more information.

---

# Release Bench

Releases can be made for [Frappe](https://github.com/frappe/frappe) apps using bench. More information about this process can be found [here](https://github.com/frappe/bench/blob/master/docs/releasing_frappe_apps.md).

---

# Bench Manager (GUI for Bench)

[Bench Manager](https://github.com/frappe/bench_manager) is a graphical user interface to emulate the functionalities of Frappe Bench. Like the command line utility it helps you install apps, manage multiple sites, update apps and much more. Install just by executing the following command in the respective bench directory.

		bench setup manager

---

# Docker

- For official images and resources [Frappe Docker](https://github.com/frappe/frappe_docker)
- Production Installation [README](https://github.com/frappe/frappe_docker/blob/develop/README.md)
- Developer Setup [README](https://github.com/frappe/frappe_docker/blob/develop/development/README.md)

---

# Guides

- [Configuring HTTPS](https://frappe.io/docs/user/en/bench/guides/configuring-https.html)
- [Using Let's Encrypt to setup HTTPS](https://frappe.io/docs/user/en/bench/guides/lets-encrypt-ssl-setup.html)
- [Diagnosing the Scheduler](https://frappe.io/docs/user/en/bench/guides/diagnosing-the-scheduler.html)
- [Change Hostname](https://frappe.io/docs/user/en/bench/guides/adding-custom-domains)
- [Manual Setup](https://frappe.io/docs/user/en/bench/guides/manual-setup.html)
- [Setup Production](https://frappe.io/docs/user/en/bench/guides/setup-production.html)
- [Setup Multitenancy](https://frappe.io/docs/user/en/bench/guides/setup-multitenancy.html)
- [Stopping Production](https://github.com/frappe/bench/wiki/Stopping-Production-and-starting-Development)

---

# Resources

- [Background Services](https://frappe.io/docs/user/en/bench/resources/background-services.html)
- [Bench Commands Cheat Sheet](https://frappe.io/docs/user/en/bench/resources/bench-commands-cheatsheet.html)
- [Bench Procfile](https://frappe.io/docs/user/en/bench/resources/bench-procfile.html)

---

# License

bench is licensed under [GNU GPLv3](LICENSE)
