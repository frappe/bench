#! /bin/bash


# Write out current crontab
crontab -l > current_cron

# Echo new cron into cron file
echo "@reboot sleep 20 && systemctl restart supervisor" >> current_cron

# Install new cron file
crontab current_cron

# Delete the temporary cron file
rm current_cron