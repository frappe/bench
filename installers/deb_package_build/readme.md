To prepare your environment for building .deb package install instruments: <br>
`sudo apt-get install build-essential devscripts debhelper` <br>
<br>
<b>Important:</b> to build .deb package archive name must be in the format $(name)\_$(version).orig.tar.gz <br> and directory within it must be named as $(name)\_$(version)<br><br>

This build uses <i>dh-virtualenv</i>. For installation please follow the [tutorial] (http://dh-virtualenv.readthedocs.org/en/0.10/tutorial.html)

To build debian package from scratch: <br>
1) make working directory (basically with any name) near archive bench_0.92.orig.tar.gz: <br>
`mkdir build_dir` <br>
2) copy debian directory in there: <br>
`cp -r debian/ build_dir/` <br>
3) change directory: <br>
`cd build_dir/` <br>
4) run package build: <br>
`debuild -us -uc` <br>
5) install resulting package: <br>
`sudo dpkg -i ../bench_0.92_amd64.deb` <br>
Please note that name of package contains your architecture so for 32-bit machines name will differ. <br>
<br>
<i>Current state</i>: runs without problems on all Ubuntu versions installing bench in `/usr/share/python/bench/bin/bench`. Fails on Debian 8 with version format conflict.

Useful links:
[Introduction to Debian Packaging](https://wiki.debian.org/IntroDebianPackaging#Step_3:_Add_the_Debian_packaging_files)
