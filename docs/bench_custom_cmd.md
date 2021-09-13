## How are Frappe Framework commands available via bench?

bench utilizes `frappe.utils.bench_manager` to get the framework's as well as those of any custom commands written in application installed in the Frappe environment. Currently, with *version 12* there are commands related to the scheduler, sites, translations and other utils in Frappe inherited by bench.


## Can I add CLI commands in my custom app and call them via bench?

Along with the framework commands, Frappe's `bench_manager` module also searches for any commands in your custom applications. Thereby, bench communicates with the respective bench's Frappe which in turn checks for available commands in all of the applications.

To make your custom command available to bench, just create a `commands` module under your parent module and write the command with a click wrapper and a variable commands which contains a list of click functions, which are your own commands. The directory structure may be visualized as:

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

