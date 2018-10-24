os_val=$(python3 get_platform.py)

if [[ $os_val == "linux" ]]
then
	line=$(head -n 1 /etc/os-release)
	if [[ $line == *"Ubuntu"* ]] 
	then
		apt update && apt upgrade -y && apt install -y zsh vim git stow python-dev python3-dev software-properties-common curl wget gcc
		wget -O - https://bootstrap.pypa.io/get-pip.py | sudo python3
		apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xF1656F24C74CD1D8
		add-apt-repository 'deb [arch=amd64,arm64,ppc64el] http://ams2.mirrors.digitalocean.com/mariadb/repo/10.3/ubuntu bionic main'
		apt update
		apt install -y mariadb-server-10.3
		apt install -y redis-server

		curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.33.11/install.sh | bash
		export NVM_DIR="$HOME/.nvm"
		[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
		[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # nvm will now run without reopening the terminal

		nvm install v10
		npm install -g yarn

		#Python3
		cd ~
		git clone https://github.com/frappe/bench --depth 1
		pip3 install --user ./bench

		folder="frappe-bench"
		if [[ ! -d "$folder" ]] 
		then
			bench init frappe-bench --python python3 #run command if folder not present in current directory 
		fi
		cd ~/frappe-bench
		folder="apps/erpnet"
		if [[ ! -d "$folder" ]] 
		then
			bench get-app erpnext #run command if erpnet folder not present in apps directory 
		fi
		bench setup requirements
		bench setup-help #check its working	
		folder="sites/frappe"
		if [[ ! -d "$folder" ]] 
		then
			bench new-site frappe #run command if frappe folder not present in sites directory 
		fi

	else
		echo "Script only for Ubuntu distribution !"
	fi
elif [[ $os_val == "darwin" ]]
then
	echo "To be available soon.."
elif [[ $os_val == "Windows" ]]
then
	echo "No support for Windows."
	echo "Switch to Ubuntu Linux."
fi


#Pre-Reqs
