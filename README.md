<div align="center">
	<img src="https://github.com/frappe/design/raw/master/logos/png/bench-logo.png" height="128">
	<h2>Bench</h2>
</div>

Bench is a command-line utility that helps you to install, update, and manage multiple sites for Frappe/ERPNext applications on [*nix systems](https://en.wikipedia.org/wiki/Unix-like) for development and production.

## Table of Contents

 - [Installation](#installation)
 - [Usage](#basic-usage)
 - [Custom Bench commands](#custom-bench-commands)
 - [Bench Manager](#bench-manager)
 - [Guides](#guides)
 - [Resources](#resources)
 - [Development](#development)
 - [License](#license)


## Installation

For instructions on how to install Frappe/ERPNext, please refer to https://github.com/frappe/frappe_docker

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


## Development

To contribute and develop on the bench CLI tool, clone this repo and create an editable install. In editable mode, you may get the following warning everytime you run a bench command:

	WARN: bench is installed in editable mode!

	This is not the recommended mode of installation for production. Instead, install the package from PyPI with: `pip install frappe-bench`


```sh
$ git clone https://github.com/frappe/bench ~/bench-repo
$ pip3 install -e ~/bench-repo
$ bench src
/Users/frappe/bench-repo
```

To clear up the editable install and switch to a stable version of bench, uninstall via pip and delete the corresponding egg file from the python path.


```sh
# Delete bench installed in editable install
$ rm -r $(find ~ -name '*.egg-info')
$ pip3 uninstall frappe-bench

# Install latest released version of bench
$ pip3 install -U frappe-bench
```

To confirm the switch, check the output of `bench src`. It should change from something like `$HOME/bench-repo` to `/usr/local/lib/python3.6/dist-packages` and stop the editable install warnings from getting triggered at every command.

## License

This repository has been released under the [GNU GPLv3 License](LICENSE).
