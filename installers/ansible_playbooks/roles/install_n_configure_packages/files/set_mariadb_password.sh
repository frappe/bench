#!/bin/bash
debconf-set-selections <<< "mariadb-server-5.5 mysql-server/root_password password $1"
debconf-set-selections <<< "mariadb-server-5.5 mysql-server/root_password_again password $1"
