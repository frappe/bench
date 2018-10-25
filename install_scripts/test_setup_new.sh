curl -O https://raw.githubusercontent.com/smeetc/bench/master/install_scripts/get_platform.py
echo "------------------------------------obtained platform script----------------------------"
os_val=$(python3 get_platform.py)
echo "------------------------------------obtained platform value----------------------------"
if [[ $os_val == "linux" ]]
then
	line=$(head -n 1 /etc/os-release)
	if [[ $line == *"Ubuntu"* ]] 
	then
		sudo apt update && sudo apt upgrade -y && sudo apt install -y zsh vim git stow python-dev python3-dev software-properties-common curl wget gcc
		echo "-----------------------------------------update and installed all dependencies------------------------------------------"
		wget -O - https://bootstrap.pypa.io/get-pip.py | sudo python3
		echo "-----------------------------------------installed pip-------------------------------------"
		sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xF1656F24C74CD1D8
		sudo add-apt-repository 'deb [arch=amd64,arm64,ppc64el] http://ams2.mirrors.digitalocean.com/mariadb/repo/10.3/ubuntu bionic main'
		echo "-----------------------------------------added mariaDB repository------------------------------------"
		sudo apt update
		sudo apt install -y mariadb-server-10.3
		echo "-----------------------------------------installed mariaDB server---------------------------------------"
		sudo apt install -y redis-server
		echo "-----------------------------------------installed redis-server--------------------------------------"

		curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.33.11/install.sh | bash
		export NVM_DIR="$HOME/.nvm"
		[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
		[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # nvm will now run without reopening the terminal
		echo "-----------------------------------------NVM installed and added to environment variable----------------------------------"
		nvm install v10
		echo "-----------------------------------------installed nvm v10---------------------------------------"
		npm install -g yarn
		echo "-----------------------------------------installed yarn------------------------------------"

		#Python3
		cd ~
		git clone https://github.com/frappe/bench --depth 1
		pip3 install --user ./bench
		echo "-----------------------------------------installed bench------------------------------------------"
		export PATH=$PATH:$HOME/.local/bin
		echo "-----------------------------------------added $HOME/.local/bin to PATH variable----------------------------------------"
		folder="frappe-bench"
		if [[ ! -d "$folder" ]] 
		then
			bench init frappe-bench --python python3 #run command if folder not present in current directory
			echo "----------------------------------------bench init run--------------------------------------------" 
		fi
		cd ~/frappe-bench
		folder="apps/erpnet"
		if [[ ! -d "$folder" ]] 
		then
			bench get-app erpnext #run command if erpnet folder not present in apps directory
			echo "----------------------------------------erpnext created----------------------------------------------" 
		fi
		bench setup requirements
		bench setup-help #check its working	
		folder="sites/frappe"
		if [[ ! -d "$folder" ]] 
		then
			bench new-site frappe #run command if frappe folder not present in sites directory
			echo "----------------------------------------frappe created----------------------------------------" 
		fi

	else
		echo "-----------------------------------------Script only for Ubuntu distribution !-------------------------------------------"
	fi
elif [[ $os_val == "darwin" ]]
then
	echo "-----------------------------------------To be available soon..------------------------------------"
elif [[ $os_val == "Windows" ]]
then
	echo "No support for Windows."
	echo "Switch to Ubuntu Linux."
fi


#Pre-Reqs
