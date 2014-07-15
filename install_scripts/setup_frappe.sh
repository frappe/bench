set -e

get_distro() {
	ARCH=$(uname -m | sed 's/x86_/amd/;s/i[3-6]86/x86/') 
	if [ -f /etc/redhat-release ]; then
		OS="centos"
		OS_VER=`cat /etc/redhat-release | cut -d" " -f3 | cut -d "." -f1`

	elif [ -f /etc/lsb-release ]; then
		. /etc/lsb-release
		OS=$DISTRIB_ID
		OS_VER=$DISTRIB_CODENAME

	elif [ -f /etc/debian_version ]; then
		. /etc/os-release
		OS="debian"  # XXX or Ubuntu??
		OS_VER=$VERSION_ID
	fi

	export OS=$OS
	export OS_VER=$OS_VER
	export ARCH=$ARCH
	echo DEBUG $OS $OS_VER $ARCH
}

add_centos_mariadb_repo() {
	echo "
[mariadb]
name = MariaDB
baseurl = http://yum.mariadb.org/5.5/centos$OS_VER-$ARCH
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1
" > /etc/yum.repos.d/mariadb.repo
}

add_ubuntu_mariadb_repo() {
	sudo apt-get update
	sudo apt-get install -y python-software-properties
	sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db
	sudo add-apt-repository "deb http://ams2.mirrors.digitalocean.com/mariadb/repo/5.5/ubuntu $OS_VER main"
}

add_debian_mariadb_repo() {
	if [ $OS_VER == "7" ]; then
		CODENAME="wheezy"
	
	elif [ $OS_VER == "6" ]; then
		CODENAME="squeeze"
	else
		echo Unsupported Debian Version
		exit 1
	fi

	sudo apt-get update
	sudo apt-get install -y python-software-properties
	sudo apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 0xcbcb082a1bb943db
	sudo add-apt-repository "deb http://ams2.mirrors.digitalocean.com/mariadb/repo/5.5/debian $CODENAME main"
}

add_maria_db_repo() {
	if [ "$OS" == "centos" ]; then
		echo DEBUG adding centos mariadb repo
		add_centos_mariadb_repo
	
	elif [ "$OS" == "debian" ]; then 
		echo DEBUG adding debian mariadb repo
		add_debian_mariadb_repo

	elif [ "$OS" == "Ubuntu" ]; then 
		echo DEBUG adding debian mariadb repo
		add_ubuntu_mariadb_repo
	else
		echo Unsupported Distribution
		exit 1
	fi
}

install_packages() {
	if [ $OS == "centos" ]; then
		sudo yum install wget -y
		add_ius_repo
		sudo yum groupinstall -y "Development tools"
		sudo yum install -y sudo yum install MariaDB-server MariaDB-client MariaDB-compat python-setuptools nginx zlib-devel bzip2-devel openssl-devel memcached postfix python27-devel python27 libxml2 libxml2-devel libxslt libxslt-devel redis MariaDB-devel libXrender libXext python27-setuptools
		wget http://downloads.sourceforge.net/project/wkhtmltopdf/0.12.1/wkhtmltox-0.12.1_linux-centos6-amd64.rpm
		sudo rpm -Uvh wkhtmltox-0.12.1_linux-centos6-amd64.rpm
		easy_install-2.7 -U pip
	
	elif [ $OS == "debian" ]; then 
		sudo apt-get update
		sudo apt-get install python-dev python-setuptools build-essential python-mysqldb git memcached ntp vim screen htop mariadb-server mariadb-common libmariadbclient-dev  libxslt1.1 libxslt1-dev redis-server libssl-dev libcrypto++-dev postfix nginx supervisor python-pip -y 

	elif [ $OS == "Ubuntu" ]; then 
		sudo apt-get update
		sudo apt-get install python-dev python-setuptools build-essential python-mysqldb git memcached ntp vim screen htop mariadb-server mariadb-common libmariadbclient-dev  libxslt1.1 libxslt1-dev redis-server libssl-dev libcrypto++-dev postfix nginx supervisor python-pip -y 
	else
		echo Unsupported Distribution
		exit 1
	fi
}

add_user() {
# Check if script is running as root and is not running as sudo. We want to skip
# this step if the user is already running this script with sudo as a non root
# user
	if [ -z $SUDO_UID ] && [ $EUID -eq 0 ]; then
		useradd -m -d /home/frappe -s $SHELL frappe
		chmod o+x /home/frappe
		chmod o+r /home/frappe
		export FRAPPE_USER="frappe"
	else
		export FRAPPE_USER="$SUDO_USER"
	fi
}

configure_mariadb_centos() {
	# Required only for CentOS, Ubuntu and Debian will show dpkg configure screen to set the password
	if [ $OS == "centos" ]; then
		echo Enter mysql root password to set:
		read -s MSQ_PASS
		mysqladmin -u root password $MSQ_PASS
	fi
}

install_supervisor_centos() {
	# Required only for CentOS, Ubuntu and Debian have them in repositories
		easy_install supervisor
		curl https://raw.githubusercontent.com/pdvyas/supervisor-initscripts/master/redhat-init-jkoppe > /etc/init.d/supervisord
		curl https://raw.githubusercontent.com/pdvyas/supervisor-initscripts/master/redhat-sysconfig-jkoppe > /etc/sysconfig/supervisord
		curl https://raw.githubusercontent.com/pdvyas/supervisor-initscripts/master/supervisord.conf > /etc/supervisord.conf
		mkdir /etc/supervisor.d
		chmod +x /etc/init.d/supervisord
		bash -c "service supervisord start || true"
}


start_services_centos() {
	service mysql start
	service redis start
	service postfix start
	service nginx start
	service memcached start
}

configure_services_centos() {
	chkconfig --add supervisord
	chkconfig redis on
	chkconfig mysql on
	chkconfig nginx on
	chkconfig supervisord on
}

add_ius_repo() {
	if [ $ARCH == "amd64" ]; then
		T_ARCH="x86_64"
	else
		T_ARCH="i386"
	fi 
	if [ $OS_VER -eq "6" ]; then
	wget http://dl.iuscommunity.org/pub/ius/stable/CentOS/$OS_VER/$T_ARCH/epel-release-6-5.noarch.rpm
	wget http://dl.iuscommunity.org/pub/ius/stable/CentOS/$OS_VER/$T_ARCH/ius-release-1.0-11.ius.centos6.noarch.rpm
	rpm -Uvh epel-release-6-5.noarch.rpm
	rpm -Uvh ius-release-1.0-11.ius.centos6.noarch.rpm
	fi
}

install_bench() {
	sudo su $FRAPPE_USER -c "cd /home/$FRAPPE_USER && git clone --branch develop https://github.com/frappe/bench"
	if hash pip-2.7; then
		PIP="pip-2.7"
	elif hash pip2.7; then
		PIP="pip2.7"
	elif hash pip2; then
		PIP="pip2"
	elif hash pip; then
		PIP="pip"
	else
		echo PIP not installed
		exit 1
	fi
	sudo $PIP install /home/$FRAPPE_USER/bench
}

get_distro
add_maria_db_repo
install_packages
add_user
if [ $OS == "centos" ]; then
	install_supervisor_centos
	configure_services_centos
	start_services_centos
	configure_mariadb_centos
fi
install_bench
