<div align="center">

![Logo](https://raw.githubusercontent.com/frappe/bench/9f76d3a39891464a8eafdbb3084828eeb5314fde/resources/logo.png)

## Bench
**CLI to manage Frappe applications**


[![Python version](https://img.shields.io/badge/python-%3E=_3.10-green.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://badge.fury.io/py/frappe-bench.svg)](https://pypi.org/project/frappe-bench)
![Platform Compatibility](https://img.shields.io/badge/platform-linux%20%7C%20macos-blue)

</div>

## Bench

Bench is a command-line utility that helps you to install, update, and manage multiple sites for Frappe applications on [*nix systems](https://en.wikipedia.org/wiki/Unix-like) for development and production.

## Key features

Bench helps you set up and manage your frappe sites with ease. Here are some of the key features:
- Initializing a new bench to work on sites and apps
- Creating a new frappe site
- Creating and installing apps that can be used on the sites
- Managing frappe sites
- Managing site backups

## Installation

A typical bench setup provides two types of environments &mdash; Development and Production.

The setup for each of these installations can be achieved in multiple ways:

 - [Containerized Installation](#containerized-installation)
 - [Manual Installation](https://docs.frappe.io/framework/user/en/tutorial/install-and-setup-bench)

We recommend using Docker Installation to setup a Production Environment. For Development, you may choose either of the two methods to setup an instance.

Otherwise, if you are looking to evaluate Frappe apps without the hassle of managing hosting yourself, you can try them on [Frappe Cloud](https://frappecloud.com/).

<div>
	<a href="https://frappecloud.com/dashboard/signup" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/try-on-fc-white.png">
			<img src="https://frappe.io/files/try-on-fc-black.png" alt="Try on Frappe Cloud" height="28" />
		</picture>
	</a>
</div>

### Containerized Installation

A Frappe instance can be setup and replicated easily using [Docker](https://docker.com). The officially supported Docker installation can be used to setup either of both Development and Production environments.

To setup either of the environments, you will need to clone the official docker repository:

```sh
git clone https://github.com/frappe/frappe_docker.git
```

A quick setup guide for both the environments can be found below. For more details, check out the [Frappe Docker Repository](https://github.com/frappe/frappe_docker).

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

## Shell Completion

Bench supports tab completion for bash and zsh.

Run interactively to pick a shell and install location:

```sh
bench completions
```

Or pass flags to skip the prompts:

```sh
bench completions --zsh
bench completions --bash
```

> **Note:** Run this from your frappe-bench directory. The command detects the bench root from the current working directory to include your installed apps' commands in the completion script.

This writes a completion script to `~/.config/bench/` and appends a `source` line to your shell rc file. Re-run it after installing new apps or upgrading bench, since the script is generated from the current command tree.


For more in-depth information on commands and their usage, follow [Commands and Usage](https://github.com/frappe/bench/blob/develop/docs/commands_and_usage.md). As for a consolidated list of bench commands, check out [Bench Usage](https://github.com/frappe/bench/blob/develop/docs/bench_usage.md).

![Help](https://raw.githubusercontent.com/frappe/bench/9f76d3a39891464a8eafdbb3084828eeb5314fde/resources/help.png)


## Custom Bench Commands

If you wish to extend the capabilities of bench with your own custom Frappe Application, you may follow [Adding Custom Bench Commands](https://github.com/frappe/bench/blob/develop/docs/bench_custom_cmd.md).


## Guides

- [Configuring HTTPS](https://docs.frappe.io/framework/user/en/bench/guides/configuring-https)
- [Using Let's Encrypt to setup HTTPS](https://docs.frappe.io/framework/user/en/bench/guides/lets-encrypt-ssl-setup)
- [Diagnosing the Scheduler](https://docs.frappe.io/framework/user/en/bench/guides/diagnosing-the-scheduler)
- [Change Hostname](https://docs.frappe.io/framework/user/en/bench/guides/adding-custom-domains)
- [Manual Setup](https://docs.frappe.io/framework/user/en/tutorial/install-and-setup-bench)
- [Setup Production](https://docs.frappe.io/framework/user/en/bench/guides/setup-production)
- [Setup Multitenancy](https://docs.frappe.io/framework/user/en/bench/guides/setup-multitenancy)
- [Stopping Production](https://github.com/frappe/bench/wiki/Stopping-Production-and-starting-Development)


## Resources

- [Bench Commands Cheat Sheet](https://docs.frappe.io/framework/user/en/bench/resources/bench-commands-cheatsheet)
- [Background Services](https://docs.frappe.io/framework/user/en/bench/resources/background-services)
- [Bench Procfile](https://docs.frappe.io/framework/user/en/bench/resources/bench-procfile)


## Development

To contribute and develop on the bench CLI tool, clone this repo and create an editable install. In editable mode, you may get the following warning everytime you run a bench command:

	WARN: bench is installed in editable mode!

	This is not the recommended mode of installation for production. Instead, install the package from PyPI with: `pip install frappe-bench`

### Clone and install

```sh
git clone https://github.com/frappe/bench ~/bench-repo
pip install -e ~/bench-repo
```

```shell
bench src
```
This should display $HOME/bench-repo

### To clear up the editable install and delete the corresponding egg file from the python path:

```sh
# Delete bench installed in editable install
pip uninstall frappe-bench
```

### Then you can install the latest from PyPI
```sh
pip install -U frappe-bench
```

To confirm the switch, check the output of `bench src`. It should change from something like `$HOME/bench-repo` to `/usr/local/lib/python3.12/dist-packages` and stop the editable install warnings from getting triggered at every command.


## Releases

Bench's version information can be accessed via `bench.VERSION` in the package's __init__.py file. Ever since the v5.0 release, we've started publishing releases on GitHub, and PyPI.

[GitHub](https://github.com/frappe/bench/releases)
[Pypi](https://pypi.org/project/frappe-bench)


## Learn and connect

- [Discuss](https://discuss.frappe.io/)
- [YouTube](https://www.youtube.com/@frappetech)

## Contribute
To contribute to this project, please review the [Contribution Guidelines](https://github.com/frappe/erpnext/wiki/Contribution-Guidelines) for detailed instructions. Make sure to follow our [Code of Conduct](https://github.com/frappe/frappe/blob/develop/CODE_OF_CONDUCT.md) to keep the community welcoming and respectful.

## Security
The Frappe team and community prioritize security. If you discover a security issue, please report it via our [Security Report Form](https://frappe.io/security).
Your responsible disclosure helps keep Frappe and its users safe. We'll do our best to respond quickly and keep you informed throughout the process.
For guidelines on reporting, check out our [Reporting Guidelines](https://frappe.io/security), and review our [Logo and Trademark Policy](https://github.com/frappe/erpnext/blob/develop/TRADEMARK_POLICY.md) for branding information.

<br/><br/>
<div align="center">
	<a href="https://frappe.io" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/Frappe-white.png">
			<img src="https://frappe.io/files/Frappe-black.png" alt="Frappe Technologies" height="28"/>
		</picture>
	</a>
</div>
