#!/bin/bash

LOG_FILES=" \
access_80.log
access_20133.log
uwsgi_80.log
uwsgi_20133.log
error.log
bar_ws.js.log
mailer_web.log
"

LOG_PATH="/usr/local/nginx/logs/"
LOG_PATH_B="/usr/local/nginx/logs/backup/"

TO_DATE=`date +%Y%m%d`

for file in $LOG_FILES
do
  cp $LOG_PATH$file $LOG_PATH_B$file.$TO_DATE
  cat /dev/null > $LOG_PATH$file
done
