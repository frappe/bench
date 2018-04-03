### ERPNext VM Builder

#### Steps to build a vm image

* Install VirtualBox
* Place a `base.ova` ubuntu base image in the current directory.
* `./packer build vm.json` builds a new vm.

#### How it works

Packer imports the base image in a virtual machine and boots it. It runs the following

* `scripts/install_ansible.sh` sets up ansible on the vm.
* The `ansible/vm.yml` playbook sets up the dependencies, installs a bench and sets up a site. It also puts it into production.
* `scripts/set_message.sh` sets welcome message (with update instructions) in the vm.
* `scripts/zerofree.sh` writes zero to all the free space in the disk, it shrinks the disk image.

#### For a build server

Running the `build.py` script builds a vm and puts it in `~/public`. It also writes a `latest.json` file in `~/public` with filename of the latest build and its md5sum.

#### Packer binary

The binary included in this tree is compiled (for linux amd64) with a fix for https://github.com/mitchellh/packer/issues/2447. We can remove it once a new version of packer is released.

