## Usage

* Updating

To update the bench CLI tool, depending on your method of installation, you may use 

	pip3 install -U frappe-bench


To backup, update all apps and sites on your bench, you may use

	bench update


To manually update the bench, run `bench update` to update all the apps, run
patches, build JS and CSS files and restart supervisor (if configured to).

You can also run the parts of the bench selectively.

`bench update --pull` will only pull changes in the apps

`bench update --patch` will only run database migrations in the apps

`bench update --build` will only build JS and CSS files for the bench

`bench update --bench` will only update the bench utility (this project)

`bench update --requirements` will only update all dependencies (Python + Node) for the apps available in current bench


* Create a new bench

	The init command will create a bench directory with frappe framework installed. It will be setup for periodic backups and auto updates once a day.

		bench init frappe-bench && cd frappe-bench

* Add a site

	Frappe apps are run by frappe sites and you will have to create at least one site. The new-site command allows you to do that.

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

* Setup Manager

## What it does

		bench setup manager

1. Create new site bench-manager.local
2. Gets the `bench_manager` app from https://github.com/frappe/bench_manager if it doesn't exist already
3. Installs the bench_manager app on the site bench-manager.local

