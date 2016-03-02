#!/bin/bash

debconf-set-selections <<< "postfix postfix/mailname string `hostname`"

