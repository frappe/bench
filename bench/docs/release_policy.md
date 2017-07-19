# Release Policy

We maintain a **staging** branch for erpnext and frappe. On every Wednesday, release team will create a **staging** branch from **develop** (Internal Release). Same on every Tuesday,we will release from **staging** branch to **master** (Community Release). We also maintain **hotfix** branch, to fix bugs from release. Hot fixes release will take place as per the priority and severity.


**I. Branch Description**

1. develop: All new feature developments will go in develop branch
2. staging: This branch serves as a release candidate. Before a week, release team will pull feature from develop branch to staging branch.<br> EG: if feature is in 25 July's milestone then it should go in staging on 19th July.
3. master: Community release.
4. hotfix: mainly define for support issues. This will include bugs or any high priority task like security patches.


**II. Where to send PR?**

1. If you are working on a new feature, then PR should point to develop branch
2. If you are working on support issue / bug / error report, then PR should point to hotfix brach
3. While performing testing on Staging branch, if any fix needed then only send that fix PR to staging.
4. Direct push to master strictly prohibited.


**III. Versioning**

1. develop to staging: No release number, cherry-pick or hard push from develop.
2. staging to master:
      Patch: Small fixes
      Minor: For new features updates.
      Major: If any API changes
3. hotfix to master: Patch version release


**IV. Release Impact on branches:**

1. Releasing from staging:
    staging -> master -> develop -> hotfix
2. Releasing from hotfix:
    hotfix -> master -> develop -> staging


**V. Servers/Sites and Branches:**

1. Frappe Cloud: master branch (Every Tuesday)
2. Frappe.io and Central: staging Branch (Every Wednesday)
3. demo.erpnext.com: master
4. beta.erpnext.com: staging

