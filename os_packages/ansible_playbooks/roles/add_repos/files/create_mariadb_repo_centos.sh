#!/bin/bash
echo "[mariadb]" > $1
echo "name = MariaDB" >> $1
OS_VER=`cat /etc/redhat-release | sed 's/Linux\ //g' | cut -d" " -f3 | cut -d. -f1`
ARCH=`uname -m | sed 's/x86_/amd/;s/i[3-6]86/x86/'`
echo "baseurl = http://yum.mariadb.org/10.0/centos$OS_VER-$ARCH" >> $1
echo "gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB" >> $1
echo "gpgcheck=1" >> $1
