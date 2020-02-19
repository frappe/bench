# bench CLI Usage

This may not be known to a lot of people but half the bench commands we're used to, exist in the Frappe Framework and not in bench directly. Those commands generally are the `--site` commands. This page is concerned only with the commands in the bench project. Any framework commands won't be a part of this consolidation.


## How are Frappe Framework commands available via bench?

bench utilizes `frappe.utils.bench_manager` to get the framework's as well as those of any custom commands written in application installed in the Frappe environment. Currently, with *version 12* there are commands related to the scheduler, sites, translations and other utils in Frappe inherited by bench.


## Can I add CLI commands in my custom app and call them via bench?

Along with the framework commands, Frappe's `bench_manager` module also searches for any commands in your custom applications. Thereby, bench communicates with the respective bench's Frappe which in turn checks for available commands in all of the applications.

To make your custom command available to bench, just create a `commands` module under your parent module and write the command with a click wrapper and a variable commands which contains a list of click functions, which are your own commands. The directory strcuture may be visualized as:

```
frappe-bench
|──apps
    |── frappe
    ├── custom_app
    │   ├── README.md
    │   ├── custom_app
    │   │   ├── commands    <------ commands module
    │   ├── license.txt
    │   ├── requirements.txt
    │   └── setup.py
```

The commands module maybe a single file such as `commands.py` or a directory with an `__init__.py` file. For a custom application of name 'flags', example may be given as

```python
# file_path: frappe-bench/apps/flags/flags/commands.py
import click

@click.command('set-flags')
@click.argument('state', type=click.Choice(['on', 'off']))
def set_flags(state):
    from flags.utils import set_flags
    set_flags(state=state)

commands = [
    set_flags
]
```

and with context of the current bench, this command maybe executed simply as

```zsh
➜ bench set-flags
Flags are set to state: 'on'
```

# bench CLI Commands

Under Click's structure, `bench` is the main command group, under which there are three main groups of commands in bench currently, namely

 - **install**: The install command group deals with commands used to install system dependencies for setting up Frappe environment

 - **setup**: This command group for consists of commands used to maipulate the requirements and environments required by your Frappe environment

 - **config**: The config command group deals with making changes in the current bench (not the CLI tool) configuration


## Using the bench command line

```zsh
➜ bench
Usage: bench [OPTIONS] COMMAND [ARGS]...

  Bench manager for Frappe

Options:
  --version
  --help     Show this message and exit.

Commands:
  backup                   Backup single site
  backup-all-sites         Backup all sites in current bench
  config                   Change bench configuration
  disable-production       Disables production environment for the bench.
  download-translations    Download latest translations
  exclude-app              Exclude app from updating
  find                     Finds benches recursively from location
  get-app                  Clone an app from the internet or filesystem and...
```

Similarly, all available flags and options can be checked for commands individually by executing them with the `--help` flag. The `init` command for instance:

```zsh
➜ bench init --help
Usage: bench init [OPTIONS] PATH

  Initialize a new bench instance in the specified path

Options:
  --python TEXT                   Path to Python Executable.
  --ignore-exist                  Ignore if Bench instance exists.
  --apps_path TEXT                path to json files with apps to install
                                  after init
```



## bench and sudo

Some bench commands may require sudo, such as some `setup` commands and everything else under the `install` commands group. For these commands, you may not be asked for your root password if sudoers setup has been done. The security implications, well we'll talk about those soon.



## General Commands

These commands belong directly to the bench group so they can be invoked directly prefixing each with `bench` in your shell. Therefore, the usage for these commands is as

```zsh
    bench COMMAND [ARGS]...
```

### The usual commands

 - **init**: Initialize a new bench instance in the specified path
 - **restart**: Restart supervisor processes or systemd units. Used in production setup
 - **update**: Updates bench tool and if executed in a bench directory, without any flags will backup, pull, setup requirements, build, run patches and restart bench. Using specific flags will only do certain tasks instead of all
 - **migrate-env**: Migrate Virtual Environment to desired Python Version
 - **retry-upgrade**: Retry a failed upgrade
 - **disable-production**: Disables production environment for the bench.
 - **renew-lets-encrypt**: Renew Let's Encrypt certificate
 - **backup**: Backup single site
 - **backup-all-sites**: Backup all sites in current bench

 - **get-app**: Clone an app from the internet or filesystem and set it up in your bench
 - **remove-app**: Completely remove app from bench and re-build assets if not installed on any site
 - **exclude-app**: Exclude app from updating
 - **include-app**: Include app for updating
 - **remote-set-url**: Set app remote url
 - **remote-reset-url**: Reset app remote url to frappe official
 - **remote-urls**: Show apps remote url
 - **switch-to-branch**: Switch all apps to specified branch, or specify apps separated by space
 - **switch-to-develop**: Switch frappe and erpnext to develop branch


### A little advanced

 - **set-nginx-port**: Set NGINX port for site
 - **set-ssl-certificate**: Set SSL certificate path for site
 - **set-ssl-key**: Set SSL certificate private key path for site
 - **set-url-root**: Set URL root for site
 - **set-mariadb-host**: Set MariaDB host for bench
 - **set-redis-cache-host**: Set Redis cache host for bench
 - **set-redis-queue-host**: Set Redis queue host for bench
 - **set-redis-socketio-host**: Set Redis socketio host for bench
 - **set-default-site**: Set default site for bench
 - **download-translations**: Download latest translations


### Developer's commands

 - **start**: Start Frappe development processes
 - **src**: Prints bench source folder path, which can be used as:  cd `bench src`
 - **find**: Finds benches recursively from location
 - **pip**: For pip help use `bench pip help [COMMAND]` or `bench pip [COMMAND] -h`
 - **new-app**: Create a new Frappe application under apps folder


### Release bench
 - **release**: Release a Frappe application
 - **prepare-beta-release**: Prepare major beta release from develop branch



## Setup commands

The setup commands used for setting up the Frappe environment in context of the current bench need to be executed using `bench setup` as the prefix. So, the general usage of these commands is as

```zsh
    bench setup COMMAND [ARGS]...
```

 - **sudoers**: Add commands to sudoers list for execution without password

 - **env**: Setup virtualenv for bench
 - **redis**: Generates configuration for Redis
 - **fonts**: Add Frappe fonts to system
 - **config**: Generate or over-write sites/common_site_config.json
 - **backups**: Add cronjob for bench backups
 - **socketio**: Setup node dependencies for socketio server
 - **requirements**: Setup Python and Node dependencies

 - **manager**: Setup bench-manager.local site with the bench_manager app installed on it

 - **procfile**: Generate Procfile for bench start

 - **production**: Setup Frappe production environment for specific user
 - **nginx**: Generate configuration files for NGINX
 - **fail2ban**: Setup fail2ban, an intrusion prevention software framework that protects computer servers from brute-force attacks
 - **systemd**: Generate configuration for systemd
 - **firewall**: Setup firewall for system
 - **ssh-port**: Set SSH Port for system
 - **reload-nginx**: Checks NGINX config file and reloads service
 - **supervisor**: Generate configuration for supervisor
 - **lets-encrypt**: Setup lets-encrypt SSL for site
 - **wildcard-ssl**: Setup wildcard SSL certificate for multi-tenant bench

 - **add-domain**: Add a custom domain to a particular site
 - **remove-domain**: Remove custom domain from a site
 - **sync-domains**: Check if there is a change in domains. If yes, updates the domains list.

 - **role**: Install dependencies via ansible roles



## Config commands

The config group commands are used for manipulating configurations in the current bench context. The usage for these commands is as

```zsh
    bench config COMMAND [ARGS]...
```

 - **set-common-config**: Set value in common config
 - **remove-common-config**: Remove specific keys from current bench's common config

 - **update_bench_on_update**: Enable/Disable bench updates on running bench update
 - **restart_supervisor_on_update**: Enable/Disable auto restart of supervisor processes
 - **restart_systemd_on_update**: Enable/Disable auto restart of systemd units
 - **dns_multitenant**: Enable/Disable bench multitenancy on running bench update
 - **serve_default_site**: Configure nginx to serve the default site on port 80
 - **http_timeout**: Set HTTP timeout



## Install commands

The install group commands are used for manipulating system level dependencies. The usage for these commands is as

```zsh
    bench install COMMAND [ARGS]...
```

 - **prerequisites**: Installs pre-requisite libraries, essential tools like b2zip, htop, screen, vim, x11-fonts, python libs, cups and Redis
 - **nodejs**: Installs Node.js v8
 - **nginx**: Installs NGINX. If user is specified, sudoers is setup for that user
 - **packer**: Installs Oracle virtualbox and packer 1.2.1
 - **psutil**: Installs psutil via pip
 - **mariadb**: Install and setup MariaDB of specified version and root password
 - **wkhtmltopdf**: Installs wkhtmltopdf v0.12.3 for linux
 - **supervisor**: Installs supervisor. If user is specified, sudoers is setup for that user
 - **fail2ban**: Install fail2ban, an intrusion prevention software framework that protects computer servers from brute-force attacks
 - **virtualbox**: Installs supervisor
