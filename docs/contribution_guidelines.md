# Contribution Guidelines

### Introduction (for first timers)

Thank you for your interest in contributing to our project! Our world works on people taking initiative to contribute to the "commons" and contributing to open source means you are contributing to make things better for not only yourself, but everyone else too! So kudos to you for taking this initiative.

Great projects depend on good code quality and adhering to certain standards while making sure the goals of the project are met. New features should follow the same pattern and so that users don't have to learn things again and again.

Developers who maintain open source also expect that you follow certain guidelines. These guidelines ensure that developers are able quickly give feedback on your contribution and how to make it better. Most probably you might have to go back and change a few things, but it will be in th interest of making this process better for everyone. So do be prepared for some back and forth.

Happy contributing!

### Feedback Policy

We will strive for a "Zero Pull Request Pending" policy, inspired by "Zero Inbox". This means, that if the pull request is good, it will be merged within a day and if it does not meet the requirements, it will be closed.

### Design Guides

Please read the following design guidelines carefully when contributing:

1. [Form Design Guidelines](https://github.com/frappe/erpnext/wiki/Form-Design-Guidelines)
1. [How to break large contributions into smaller ones](https://github.com/frappe/erpnext/wiki/Cascading-Pull-Requests)

### Pull Request Requirements

1. **Test Cases:** Important to add test cases, even if its a very simple one that just calls the function. For UI, till we don't have Selenium testing setup, we need to see a screenshot / animated GIF.
1. **UX:** If your change involves user experience, add a screenshot / narration / animated GIF.
1. **Documentation:** Test Case must involve updating necessary documentation
1. **Explanation:** Include explanation if there is a design change, explain the use case and why this suggested change is better. If you are including a new library or replacing one, please give sufficient reference of why the suggested library is better.
1. **Demo:** Remember to update the demo script so that data related your feature is included in the demo.
1. **Failing Tests:** This is simple, you must make sure all automated tests are passing.
1. **Very Large Contribution:** It is very hard to accept and merge very large contributions, because there are too many lines of code to check and its implications can be large and unexpected. They way to contribute big features is to build them part by part. We can understand there are exceptions, but in most cases try and keep your pull-request to **30 lines of code** excluding tests and config files. **Use [Cascading Pull Requests](https://github.com/frappe/erpnext/wiki/Cascading-Pull-Requests)** for large features.
1. **Incomplete Contributions must be hidden:** If the contribution is WIP or incomplete - which will most likely be the case, you can send small PRs as long as the user is not exposed to unfinished functionality. This will ensure that your code does not have build or other collateral issues. But these features must remain completely hidden to the user.
1. **Incorrect Patches:** If your design involves schema change and you must include patches that update the data as per your new schema.
1. **Incorrect Naming:** The naming of variables, models, fields etc must be consistent as per the existing design and semantics used in the system.
1. **Translated Strings:** All user facing strings / text must be wrapped in the `__("")` function in javascript and `_("")` function in Python, so that it is shown as translated to the user.
1. **Deprecated API:** The API used in the pull request must be the latest recommended methods and usage of globals like `cur_frm` must be avoided.
1. **Whitespace and indentation:** The ERPNext and Frappe Project uses tabs (I know and we are sorry, but its too much effort to change it now and we don't want to lose the history). The indentation must be consistent whether you are writing Javascript or Python. Multi-line strings or expressions must also be consistently indented, not hanging like a bee hive at the end of the line. We just think the code looks a lot more stable that way.

#### What if my Pull Request is closed?

Don't worry, fix the problem and re-open it!

#### Why do we follow this policy?

This is because ERPNext is at a stage where it is being used by thousands of companies and introducing breaking changes can be harmful for everyone. Also we do not want to stop the speed of contributions and the best way to encourage contributors is to give fast feedback.