#!/bin/bash

debconf-set-selections <<< "postfix postfix/main_mailer_type string 'Internet Site'"
