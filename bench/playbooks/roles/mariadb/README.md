# Ansible Role: MariaDB

Installs MariaDB

## Supported platforms

```
CentOS 6 & 7
Ubuntu 14.04
Ubuntu 16.04
Debain 9
```

## Post install

Run `mariadb-secure-installation`

## Requirements

None

## Role Variables

MariaDB version:

```
mariadb_version: 10.2
```

Configuration template:

```
mysql_conf_tpl: change_me
```

Configuration filename:

```
mysql_conf_file: settings.cnf
```

### Experimental unattended mariadb-secure-installation

```
ansible-playbook release.yml --extra-vars "mysql_secure_installation=true mysql_root_password=your_very_secret_password"
```

## Dependencies

None

## Example Playbook

```
- hosts: servers
  roles:
    - { role: mariadb }
```

## Credits

- [Attila van der Velde](https://github.com/vdvm)

