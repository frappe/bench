# Release Policy

#### Create staging branch

- On Wednesday morning, we will create a `staging` branch from develop branch. `staging` branch is a release candidate. All new features will first go from `develop` to `staging` and then `staging` to `master`.

- Use the prepare-staging command to create staging branch
```usage: bench prepare-staging APP```

- Impact on branches ?
  - merge all commits from develop branch to staging
  - push merge commit back to develop

- QA will use staging for testing.

- Deploy staging branch on frappe.io

- Only regression and security fixes can be cherry-picked into staging

- Create a discuss post on what all new features or fixes going in next version.

---

#### Create release from staging
- On Tuesday, we will release from staging to master.

- Versioning:
  - patch: Small fixes
  - minor: For new features updates.
  - major: If any API changes

- Impact on branches:
  - merge staging branch to master
  - push merge commit back to staging branch
  - push merge commit to develop branch
  - push merge commit to hotfix branch

- Use release command to create release,
``` usage: bench release APP patch|minor|major --from-branch staging ```

---

#### Create release from hotfix
- Depending on priority, hotfix release will take place.

- Versioning:
  - patch: Small fixes

- Impact on branches:
  - merge hotfix branch to master
  - push merge commit back to staging branch
  - push merge commit to develop branch
  - push merge commit to staging branch

- Use release command to create release,
``` usage: bench release APP patch --from-branch hotfix ```
