#!/bin/bash

res=$(chkconfig | grep $1 | awk 'BEGIN {RS = ":"}; {print $0}' | grep `runlevel | cut -d" " -f2` | grep on | wc -l)
echo -n $res
