The playbook main.yml contains two roles: add_repos and install_packages. It's configured to work with Debian, Ubuntu and CentOS. <br>
Additional playbook wkhtmltopdf.yml is for optional package wkhtmltopdf. <br>
<br>
To use ansible playbooks: <br>
1. install ansible following the [tutorial](http://docs.ansible.com/ansible/intro_installation.html) <br>
2. add the following lines to file `/etc/ansible/hosts` for installation on local machine: <br>
`[local]` <br>
`localhost ansible_connection=local` <br>
3. run ansible-playbook: <br>
`ansible-playbook main.yml` to prepare environment for bench package<br>
or `ansible-playbook wkhtmltopdf.yml` to install optional package wkhtmltopdf.
