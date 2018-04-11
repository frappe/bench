## ERPNext VM Builder


### Steps to build a VM Image

* `python build.py` builds a new Production VM, a Dev VM and a Dev Vagrant Box


### Requirements 

* Bench should be installed
* Ansible should be installed


### How it works

Apart from the above the rest is handled by bench:

* Install prerequisites if not already installed
	- virtualbox
	- packer
* Cleanup
	- Clean the required directories
* Build the VM using packer
	- Packer downloads the mentioned Ubuntu iso, boots a virtual machine and preceeds the preseed.cfg file into it in order to setup a clean Ubuntu OS
	- Then packer uses ssh to enter the virtual machine to execute the required commands
	- `scripts/debian_family/install_ansible.sh` sets up ansible on the vm.
	- Depending on the VM being built, the `vm-develop.json` or the `vm-production.json` is used
	- `scripts/set_message.sh` sets welcome message (with update instructions) in the vm.
	- `scripts/cleanup.sh` writes zeros to all the free space in the disk, it shrinks the disk image
* Set the correct permissions for the built Vagrant and Virtual Appliance Images
* Cleanup
	- Delete the generated files from the required directories
* Restart nginx 


Running the `build.py` script builds the VMs and puts them in `~/Public`. It also creates the md5 hashes for the same, and puts them in the same folder.
