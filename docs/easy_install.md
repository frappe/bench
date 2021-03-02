# Easy Install Script

- This script will install the pre-requisites, install bench and setup an ERPNext site `(site1.local under frappe-bench)`
- Passwords for Frappe Administrator and MariaDB (root) will be asked and saved under `~/passwords.txt`
- MariaDB (root) password may be `password` on a fresh server
- You can then login as **Administrator** with the Administrator password
- The log file is saved under `/tmp/logs/install_bench.log` in case you run into any issues during the install.
- If you find any problems, post them on the forum: [https://discuss.erpnext.com](https://discuss.erpnext.com/tags/installation_problem) under the "Install / Update" category.

---

## What will this script do?

- Install all the pre-requisites
- Install the command line `bench` (under ~/.bench)
- Create a new bench (a folder that will contain your entire frappe/erpnext setup at ~/frappe-bench)
- Create a new ERPNext site on the bench (site1.local)

---

## Getting started with easy install...

Open your Terminal and enter:

#### 0. Setup user & Download the install script

If you are on a fresh server and logged in as root, at first create a dedicated user for frappe
& equip this user with sudo privileges

```
  adduser [frappe-user]
  usermod -aG sudo [frappe-user]
```

*(it is very common to use "frappe" as frappe-username, but this comes with the security flaw of ["frappe" ranking very high](https://www.reddit.com/r/dataisbeautiful/comments/b3sirt/i_deployed_over_a_dozen_cyber_honeypots_all_over/?st=JTJ0SC0Q&sh=76e05240) in as a username challenged in hacking attempts. So, for production sites it is highly recommended to use a custom username harder to guess)*

*(you can specify the flag --home to specify a directory for your [frappe-user]. Bench will follow the home directory specified by the user's home directory e.g. /data/[frappe-user]/frappe-bench)*

Switch to `[frappe-user]` (using `su [frappe-user]`) and start the setup

	wget https://raw.githubusercontent.com/frappe/bench/develop/install.py


#### 1. Run the install script

	sudo python3 install.py

*Note: `user` flag to create a user and install using that user (By default, the script will create a user with the username `frappe` if the --user flag is not used)*

For production or development, append the `--production` or `--develop` flag to the command respectively.

	sudo python3 install.py --production --user [frappe-user]

or

	sudo python3 install.py --develop
	sudo python3 install.py --develop --user [frappe-user]

	sudo python3 install.py --production --user [frappe-user] --container

*Note: `container` flag to install inside a container (this will prevent the `/proc/sys/vm/swappiness: Read-only` file system error)*


	python3 install.py --production --version 11 --user [frappe-user]

use --version flag to install specific version

	python3 install.py --production --version 11 --python python2.7 --user [frappe-user]

use --python flag to specify virtual environments python version, by default script setup python3

---

## How do I start ERPNext

1. For development: Go to your bench folder (`~[frappe-user]/frappe-bench` by default) and start the bench with `bench start`
2. For production: Your process will be setup and managed by `nginx` and `supervisor`. Checkout [Setup Production](https://frappe.io/docs/user/en/bench/guides/setup-production.html) for more information.

---

## An error occured mid installation?

TLDR; Save the logs!

1. The easy install script starts multiple processes to install prerequisites, system dependencies, requirements, sets up locales, configuration files, etc.

2. The script pipes all these process outputs and saves it under `/tmp/log/{easy-install-filename}.log` as prompted by the script in the beginning of the script or/and if something went wrong again.

3. Retain this log file and share it in case you need help with proceeding with the install. Since, the file's saved under `/tmp` it'll be cleared by the system after a reboot. Be careful to save it elsewhere if needed!

3. A lot of things can go wrong in setting up the environment due to prior settings, company protocols or even breaking changes in system packages and their dependencies.

4. Sharing your logfile in any issues opened related to this can help us find solutions to it faster and make the script better!
