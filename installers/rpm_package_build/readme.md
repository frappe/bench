<b>Important</b>:
* archive name must be in the format $(name)-$(version).tar.gz
and directory within it must be named as $(name)-$(version) <br>
* filename of the .spec file must be exactly as a package name, do not change it <br>
* do not run `rpmdev-setuptree` and `rpmbuild` as a root user <br>

<i>To prepare</i> your environment for building .rpm package do the following: <br>
1. install instruments: <br>
`sudo yum install epel-release rpmdevtools yum-utils` <br>
2. create directory hierarchy for rpm (this will create directory ~/rpmbuild with the subdirectories BUILD RPMS SOURCES SPECS SRPMS): <br>
`rpmdev-setuptree` <br>
3. place `bench.spec` into ~/rpmbuild/SPECS <br>
4. place  `bench-0.92.tar.gz` into ~/rpmbuild/SOURCES <br>
5. install all required for .rpm building dependencies: <br>
`yum-builddep ~/rpmbuild/SPECS/bench.spec`
<br>

<i>To build</i> .rpm package run: <br>
`rpmbuild -ba ~/rpmbuild/SPECS/bench.spec` <br>
The resulting .rpm will be in `~/rpmbuild/RPMS/` and .srpm in `~/rpmbuild/SRPMS`

<i>To install</i> .rpm package run: <br>
`sudo yum localinstall path/to/rpm/package` <br>
<br>
<i>Current state:</i> builds ok but resulting bench fails with the error: <br>
`Traceback (most recent call last):` <br>
`File "/usr/bin/bench", line 7, in <module>` <br>
`from bench.cli import cli` <br>
`ImportError: No module named bench.cli` <br>

Useful links:
[rpm packaging tutorial] (http://www.ibm.com/developerworks/library/l-rpm1/)






