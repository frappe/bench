#!/bin/bash
set -e

# stolen from http://cgit.drupalcode.org/octopus/commit/?id=db4f837
includedir=`mysql_config --variable=pkgincludedir`
thiscwd=`pwd`
_THIS_DB_VERSION=`mysql -V 2>&1 | tr -d "\n" | cut -d" " -f6 | awk '{ print $1}' | cut -d"-" -f1 | awk '{ print $1}' | sed "s/[\,']//g"`
LOG_FILE=`readlink -m "$includedir/$_THIS_DB_VERSION-fixed.log"`
if [ "$_THIS_DB_VERSION" = "5.5.40" ] && [ ! -e $LOG_FILE ] ; then
  cd $includedir
  sudo patch -p1 < $thiscwd/my_config.h.patch &> /dev/null
  sudo touch $LOG_FILE
fi
