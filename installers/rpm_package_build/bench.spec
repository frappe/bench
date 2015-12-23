%define name bench
%define version 0.92
%define unmangled_version 0.92
%define unmangled_version 0.92
%define release 1
%define _buildshell /bin/bash

Summary: Metadata driven, full-stack web framework
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: GPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Frappe Technologies <info@frappe.io>
Url: https://github.com/frappe/bench

# for building/installing the package
BuildRequires:	python, python-wheel

# centos 6 dependencies
%if 0%{rhel} == 6
Requires:	git, MariaDB-server, MariaDB-client, MariaDB-compat, python-setuptools, nginx
Requires:	zlib-devel, bzip2-devel, openssl-devel, postfix, python27-devel, python27
Requires:	libxml2, libxml2-devel, libxslt, libxslt-devel, redis, MariaDB-devel, libXrender, libXext
Requires:	python27-setuptools, cronie, sudo, which, xorg-x11-fonts-Type1, xorg-x11-fonts-75dpi, nodejs, npm
Requires:	libtiff-devel, libjpeg-devel, libzip-devel, freetype-devel, lcms2-devel, libwebp-devel, tcl-devel, tk-devel
%endif

# centos 7 dependencies
%if 0%{rhel} == 7
Requires:	git, mariadb-server, mariadb-devel, python-setuptools, nginx
Requires:	zlib-devel, bzip2-devel, openssl-devel, postfix, python-devel
Requires:	libxml2, libxml2-devel, libxslt, libxslt-devel, redis, libXrender, libXext
Requires:	supervisor, cronie, sudo, which, xorg-x11-fonts-75dpi, xorg-x11-fonts-Type1, nodejs, npm
Requires:	libtiff-devel, libjpeg-devel, libzip-devel, freetype-devel, lcms2-devel, libwebp-devel, tcl-devel, tk-devel
%endif

%description
UNKNOWN

%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}
python setup.py bdist_wheel

%install
# directory for bench installation
mkdir -p build
# the following is to install bench locally
export ppath=`pwd`/build
export PYTHONPATH=$ppath 
export whl_file=`find . -type f -name *.whl`
pip install --root=$ppath $whl_file
# pip installed bench, now moving it to appropriate location in %{buildroot}
mkdir -p %{buildroot}/usr/bin
cp build/usr/bin/bench %{buildroot}/usr/bin/


%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%doc MANIFEST.in LICENSE.md README.md
/usr/bin/bench
