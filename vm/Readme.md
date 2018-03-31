### ERPNext VM Builder


#### Steps to build a VM Image

* `python build.py` builds a new VM


#### Requirements 

* Bench should be installed.
* Ansible should be installed


#### How it works

Apart from the above the rest is handled by bench:

* Install prerequisites if not already installed
	- virtualbox
	- packer
* Cleanup
	- Clean the required directories
* Generate the erpnext_develop.json and the erpnext_production.json
	- Figure out the latest ubuntu iso available, get it's link and the checksum and generate the json files
* Build the VM using packer
	- Packer downloads the mentioned Ubuntu iso, boots a virtual machine and preceeds the preseed.cfg file into it in order to setup a clean Ubuntu OS
	- Then packer uses ssh to enter the virtual machine to execute the required commands
	- `scripts/debian_family/install_ansible.sh` sets up ansible on the vm.
	- Depending on the VM being built, the `install_erpnext_develop.sh` or the `install_erpnext_production.sh` is executed
	- `scripts/set_message.sh` sets welcome message (with update instructions) in the vm.
	- `scripts/cleanup.sh` writes zero to all the free space in the disk, it shrinks the disk image
* Set the correct permissions for the built Vagrant and Virtual Appliance Images
* Cleanup
	- Delete the generated files from the required directories
* restart nginx 

The requirements for this to run are Packer and Virtualbox.  imports the base image in a virtual machine and boots it. It runs the following


#### For a build server

Running the `build.py` script builds a vm and puts it in `~/public`. It also writes a `latest.json` file in `~/public` with filename of the latest build and its md5sum.
