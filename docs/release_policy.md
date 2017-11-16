# Release Policy

#### Definitions:
 - `develop` Branch: All new feature developments will go in develop branch
 - `staging` Branch: This branch serves as a release candidate. Before a week, release team will pull the feature from develop branch to staging branch.
    EG: if the feature is in 25 July's milestone then it should go in staging on 19th July.
 - `master` Branch: `master` branch serves as a stable branch. This will use as production deployment.
 - `hotfix` Branch: mainly define for support issues. This will include bugs or any high priority task like security patches.

#### Create release from staging
- On Tuesday, we will release from staging to master.

- Versioning: Given a version number MAJOR.MINOR.PATCH, increment the:
  - MAJOR version when you make incompatible API changes,
  - MINOR version when you add functionality in a backwards-compatible manner, and
  - PATCH version when you make backwards-compatible bug fixes.

- Impact on branches:
  - merge staging branch to master
  - push merge commit back to staging branch
  - push merge commit to develop branch
  - push merge commit to hotfix branch

- Use release command to create release,
``` usage: bench release APP patch|minor|major --from-branch staging ```

---

#### Create staging branch

- On Wednesday morning, `develop` will be merge into `staging`. `staging` branch is a release candidate. All new features will first go from `develop` to `staging` and then `staging` to `master`.

- Use the prepare-staging command to create staging branch
```usage: bench prepare-staging APP```

- Impact on branches?
  - merge all commits from develop branch to staging
  - push merge commit back to develop

- QA will use staging for testing.

- Deploy staging branch on frappe.io, erpnext.org, frappe.erpnext.com. 

- Only regression and security fixes can be cherry-picked into staging

- Create a discuss post on what all new features or fixes going in next version.

---

#### Create release from hotfix
- Depending on priority, hotfix release will take place.

- Versioning:
  - PATCH version when you make backwards-compatible bug fixes.

- Impact on branches:
  - merge hotfix branch to master
  - push merge commit back to staging branch
  - push merge commit to develop branch
  - push merge commit to staging branch

- Use release command to create release,
``` usage: bench release APP patch --from-branch hotfix ```
