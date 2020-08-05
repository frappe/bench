<div align="center">
	<img src="https://github.com/frappe/design/raw/master/logos/png/bench-logo.png" height="128">
	<h2>Bench</h2>
</div>

Bench is a command-line utility that helps you to install, update, and manage multiple sites for Frappe/ERPNext applications on [*nix systems](https://en.wikipedia.org/wiki/Unix-like) for development and production.

## Table of Contents

 - [Installation](#installation)
	- [Docker Installation](#docker-installation)
		- [Development Setup](#docker-installation-for-development)
		- [Production Setup](#docker-installation-for-production)
	- [Easy Install Script](#easy-install-script)
	- [Manual Installation](#manual-installation)
 - [Usage](#usage)
 - [Custom Bench commands](#custom-bench-commands)
 - [Bench Manager](#bench-manager)
 - [Guides](#guides)
 - [Resources](#resources)
 - [License](#license)


## Installation

A typical bench setup provides two types of environments &mdash; Development and Production.

The setup for each of these installations can be achieved in multiple ways:

 - [Docker Installation](#docker-installation)
 - [Easy Install Script](#easy-install-script)
 - [Manual Installation](#manual-installation)

We recommend using either the Docker Installation or the Easy Install Script to setup a Production Environment. For Development, you may choose either of the three methods to setup an instance.

Otherwise, if you are looking to evaluate ERPNext, you can also download the [Virtual Machine Image](https://erpnext.com/download) or register for [a free trial on erpnext.com](https://erpnext.com/pricing).


### Docker Installation

A Frappe/ERPNext instance can be setup and replicated easily using [Docker](https://docker.com). The officially supported Docker installation can be used to setup either of both Development and Production environments.

To setup either of the environments, you will need to clone the official docker repository:

```sh
$ git clone https://github.com/frappe/frappe_docker.git
$ cd frappe_docker
```

A quick setup guide for both the envionments can be found below. For more details, check out the [Frappe/ERPNext Docker Repository](https://github.com/frappe/frappe_docker).

#### Docker Installation for Development

To setup a development environment for Docker, follow the [Frappe/ERPNext Docker for Development Guide](https://github.com/frappe/frappe_docker/blob/develop/development/README.md).

#### Docker Installation for Production

Copy the `env-example` file to `.env`

```sh
$ cp env-example .env
```

Optionally, you may also setup an [NGINX Proxy for SSL Certificates](https://github.com/evertramos/docker-compose-letsencrypt-nginx-proxy-companion) with auto-renewal for your Production instance. We recommend this for instances being accessed over the internet. For this to work, the DNS needs to be configured correctly so that [LetsEncrypt](https://letsencrypt.org) can verify the domain. To setup the proxy, run the following commands:

```sh
$ git clone https://github.com/evertramos/docker-compose-letsencrypt-nginx-proxy-companion.git
$ cd docker-compose-letsencrypt-nginx-proxy-companion
$ cp .env.sample .env
$ ./start.sh
```

To get the Production instance running, run the following command:

```sh
$ docker-compose \
    --project-name <project-name> \
    -f installation/docker-compose-common.yml \
    -f installation/docker-compose-erpnext.yml \
    -f installation/docker-compose-networks.yml \
    --project-directory installation up -d
```

Make sure to replace `<project-name>` with whatever you wish to call it. This should get the instance running through docker. Now, to create a new site on the instance you may run:

```sh
docker exec -it \
    -e "SITE_NAME=$SITE_NAME" \
    -e "DB_ROOT_USER=$DB_ROOT_USER" \
    -e "MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD" \
    -e "ADMIN_PASSWORD=$ADMIN_PASSWORD" \
    -e "INSTALL_APPS=erpnext" \ # optional, if you want to install any other apps
    <project-name>_erpnext-python_1 docker-entrypoint.sh new
```

Once this is done, you may access the instance at `$SITE_NAME`.

**Note:** The Production setup does not contain, require, or use bench. For a list of substitute commands, check out the [Frappe/ERPNext Docker Site Operations](https://github.com/frappe/frappe_docker/#site-operations).


### Easy Install Script

The Easy Install script should get you going with a Frappe/ERPNext setup with minimal manual intervention and effort. Since there are a lot of configurations being automatically setup, we recommend executing this script on a fresh server.

**Note:** This script works only on GNU/Linux based server distributions, and has been designed and tested to work on Ubuntu 16.04+, CentOS 7+, and Debian-based systems.

#### Prerequisites

You need to install the following packages for the script to run:

 - ##### Ubuntu and Debian-based Distributions:

	```sh
	$ apt install python3-minimal build-essential python3-setuptools
	```

 - ##### CentOS and other RPM Distributions:

	```sh
	$ dnf groupinstall "Development Tools"
	$ dnf install python3
	```

#### Setup

Download the Easy Install script and execute it:

```sh
$ wget https://raw.githubusercontent.com/frappe/bench/develop/install.py
$ python3 install.py --production
```

The script should then prompt you for the MySQL root password and an Administrator password for the Frappe/ERPNext instance, which will then be saved under `$HOME/passwords.txt` of the user used to setup the instance. This script will then install the required stack, setup bench and a default ERPNext instance.

When the setup is complete, you will be able to access the system at `http://<your-server-ip>`, wherein you can use the administrator password to login.

#### Troubleshooting

In case the setup fails, the log file is saved under `/tmp/logs/install_bench.log`. You may then:

 - Create an Issue in this repository with the log file attached.
 - Search for an existing issue or post the log file on the [Frappe/ERPNext Discuss Forum](https://discuss.erpnext.com/c/bench) with the tag `installation_problem` under "Install/Update" category.

For more information and advanced setup instructions, check out the [Easy Install Documentation](https://github.com/frappe/bench/blob/develop/docs/easy_install.md).


### Manual Installation

Some might want to manually setup a bench instance locally for development. To quickly get started on installing bench the hard way, you can follow the guide on [Installing Bench and the Frappe Framework](https://frappe.io/docs/user/en/installation).

You'll have to set up the system dependencies required for setting up a Frappe Environment. Checkout [docs/installation](https://github.com/frappe/bench/blob/develop/docs/installation.md) for more information on this. If you've already set up, install bench via pip:


```sh
$ pip install frappe-bench
```

For more extensive distribution-dependent documentation, check out the following guides:

 - [Hitchhiker's Guide to Installing Frappe on Linux](https://github.com/frappe/frappe/wiki/The-Hitchhiker%27s-Guide-to-Installing-Frappe-on-Linux)
 - [Hitchhiker's Guide to Installing Frappe on MacOS](https://github.com/frappe/bench/wiki/Setting-up-a-Mac-for-Frappe-ERPNext-Development)


## Basic Usage

**Note:** Apart from `bench init`, all other bench commands are expected to be run in the respective bench directory.

 * Create a new bench:

	```sh
	$ bench init [bench-name]
	```

 * Add a site under current bench:

	```sh
	$ bench new-site [site-name]
	```
	- **Optional**: If the database for the site does not reside on localhost or listens on a custom port, you can use the flags `--db-host` to set a custom host and/or `--db-port` to set a custom port.

		```sh
		$ bench new-site [site-name] --db-host [custom-db-host-ip] --db-port [custom-db-port]
		```

 * Download and add applications to bench:

	```sh
	$ bench get-app [app-name] [app-link]
	```

 * Install apps on a particular site

	```sh
	$ bench --site [site-name] install-app [app-name]
	```

 * Start bench (only for development)

	```sh
	$ bench start
	```

 * Show bench help:

	```sh
	$ bench --help
	```


For more in-depth information on commands and their usage, follow [Commands and Usage](https://github.com/frappe/bench/blob/develop/docs/commands_and_usage.md). As for a consolidated list of bench commands, check out [Bench Usage](https://github.com/frappe/bench/blob/develop/docs/bench_usage.md).


## Custom Bench Commands

If you wish to extend the capabilities of bench with your own custom Frappe Application, you may follow [Adding Custom Bench Commands](https://github.com/frappe/bench/blob/develop/docs/bench_custom_cmd.md).


## Bench Manager

[Bench Manager](https://github.com/frappe/bench_manager) is a GUI frontend for Bench with the same functionalties. You can install it by executing the following command:

```sh
$ bench setup manager
```

 - **Note:** This will create a new site to setup Bench Manager, if you want to set it up on an existing site, run the following commands:

	```sh
	$ bench get-app https://github.com/frappe/bench_manager.git
	$ bench --site <sitename> install-app bench_manager
	```


## Guides

- [Configuring HTTPS](https://frappe.io/docs/user/en/bench/guides/configuring-https.html)
- [Using Let's Encrypt to setup HTTPS](https://frappe.io/docs/user/en/bench/guides/lets-encrypt-ssl-setup.html)
- [Diagnosing the Scheduler](https://frappe.io/docs/user/en/bench/guides/diagnosing-the-scheduler.html)
- [Change Hostname](https://frappe.io/docs/user/en/bench/guides/adding-custom-domains)
- [Manual Setup](https://frappe.io/docs/user/en/bench/guides/manual-setup.html)
- [Setup Production](https://frappe.io/docs/user/en/bench/guides/setup-production.html)
- [Setup Multitenancy](https://frappe.io/docs/user/en/bench/guides/setup-multitenancy.html)
- [Stopping Production](https://github.com/frappe/bench/wiki/Stopping-Production-and-starting-Development)

For an exhaustive list of guides, check out [Bench Guides](https://frappe.io/docs/user/en/bench/guides).


## Resources

- [Bench Commands Cheat Sheet](https://frappe.io/docs/user/en/bench/resources/bench-commands-cheatsheet.html)
- [Background Services](https://frappe.io/docs/user/en/bench/resources/background-services.html)
- [Bench Procfile](https://frappe.io/docs/user/en/bench/resources/bench-procfile.html)

For an exhaustive list of resources, check out [Bench Resources](https://frappe.io/docs/user/en/bench/resources).


## License

This repository has been released under the [GNU GPLv3 License](LICENSE).
