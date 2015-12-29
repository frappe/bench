To prepare your environment for building .deb package install instruments: <br>
`sudo apt-get install build-essential devscripts debhelper` <br>
<br>
<b>Important:</b> to build .deb package archive name must be in the format $(name)\_$(version).orig.tar.gz <br> and directory within it must be named as $(name)\_$(version)<br><br>

This build uses <i>dh-virtualenv</i>. For installation please follow the [tutorial] (http://dh-virtualenv.readthedocs.org/en/0.10/tutorial.html)

To build debian package from scratch: <br>
1) unpack archive bench_0.92.orig.tar.gz: <br>
`tar -xf bench_0.92.orig.tar.gz` <br>
2) copy debian directory in there: <br>
`cp -r debian/ bench_0.92/` <br>
3) change directory: <br>
`cd bench_0.92/` <br>
4) run package build: <br>
`dpkg-buildpackage -us -uc` <br>
5) package is: `../bench_0.92_amd64.deb`<br>
<br>
If you don't have `gdebi` installed, first you need to run:<br>
`sudo apt-get install gdebi-core`<br>
To install resulting package with all it's dependencies: <br>
`sudo gdebi ../bench_0.92_amd64.deb` <br>
Please note that name of package contains your architecture so for 32-bit machines name will differ. <br>
<br>
<i>Current state</i>: .deb package is installed without problems on all target systems with all dependencies. Build of .deb package fails on Debian8 with version conflict error (because of quilt format), but works on all other platforms.

Useful links:
[Introduction to Debian Packaging](https://wiki.debian.org/IntroDebianPackaging#Step_3:_Add_the_Debian_packaging_files)
