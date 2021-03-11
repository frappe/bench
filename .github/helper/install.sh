#!/bin/bash

pip install urllib3 pyOpenSSL ndg-httpsclient pyasn1

# install redis
sudo apt-get install redis-server

echo "TEST"
echo $TEST

if [ $TEST == "bench" ];then
    wget -q -O /tmp/wkhtmltox.tar.xz https://github.com/frappe/wkhtmltopdf/raw/master/wkhtmltox-0.12.3_linux-generic-amd64.tar.xz;
    tar -xf /tmp/wkhtmltox.tar.xz -C /tmp;
    sudo mv /tmp/wkhtmltox/bin/wkhtmltopdf /usr/local/bin/wkhtmltopdf;
    sudo chmod o+x /usr/local/bin/wkhtmltopdf;

    mkdir -p ~/.bench;
    cp -r ${GITHUB_WORKSPACE}/* ~/.bench;
    pip install -q -U -e ~/.bench;
    sudo pip install -q -U -e ~/.bench;

    mysql --host 127.0.0.1 --port 3306 -u root -e "SET GLOBAL character_set_server = 'utf8mb4'";
    mysql --host 127.0.0.1 --port 3306 -u root -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'";
    mysql --host 127.0.0.1 --port 3306 -u root -e "UPDATE mysql.user SET Password=PASSWORD('travis') WHERE User='root'";
    mysql --host 127.0.0.1 --port 3306 -u root -e "FLUSH PRIVILEGES";
fi

if [ $TEST == "easy_install" ];then
    mkdir -p /tmp/.bench;
    cp -r ${GITHUB_WORKSPACE}/* /tmp/.bench;
fi