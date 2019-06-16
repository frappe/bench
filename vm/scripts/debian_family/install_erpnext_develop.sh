#!/bin/bash -eux

# Install ERPNext
wget https://raw.githubusercontent.com/frappe/bench/master/playbooks/install.py
python install.py --develop --user frappe --mysql-root-password frappe --admin-password admin