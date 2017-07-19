# Releasing Frappe ERPNext

* Make a new bench dedicated for releasing
```
bench init release-bench --frappe-path git@github.com:frappe/frappe.git
```

* Get ERPNext in the release bench
```
bench get-app erpnext git@github.com:frappe/erpnext.git
```

* Configure as release bench. Add this to the common_site_config.json
```
"release_bench": true,
```

* Use the release commands to release
```
Usage: bench release [OPTIONS] APP BUMP_TYPE
```

* Arguments :
  * _APP_ App name e.g [frappe|erpnext|yourapp]
  * _BUMP_TYPE_ [major|minor|patch|stable|prerelease]
* Options:
  * --develop git develop branch, default is develop
  * --master git master branch, default is master
  * --remote git remote, default is upstream
  * --owner git owner, default is frappe
  * --repo-name git repo name if different from app name