### ERPNext/Frappe Branching

#### Branch Description
 - `develop` Branch: All new feature developments will go in develop branch
 - `staging` Branch: This branch serves as a release candidate. Before a week, release team will pull the feature from develop branch to staging branch.
    EG: if the feature is in 25 July's milestone then it should go in staging on 19th July.
 - `master` Branch: Community release.
 - `hotfix` Branch: mainly define for support issues. This will include bugs or any high priority task like security patches.

#### Where to send PR?
 - If you are working on a new feature, then PR should point to develop branch
 - If you are working on support issue / bug / error report, then PR should point to hotfix brach
 - While performing testing on Staging branch, if any fix needed then only send that fix PR to staging.