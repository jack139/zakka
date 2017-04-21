#!/usr/bin/env python
# -*- coding: utf-8 -*-
import web
from pymongo import MongoClient

#####
debug_mode = True   # Flase - production, True - staging
#####

# '192.168.1.98','192.168.1.98'
web_serv_list={'web1' : ('10.132.59.223','121.199.61.11')}  # ÄÚÍø£¬ÍâÍø
#file_serv_list={'file1': ('10.132.59.223','121.199.61.11')}

local_ip=web_serv_list['web1'][1]

cli = {'web'  : MongoClient(web_serv_list['web1'][0]),
#       'file1': MongoClient(file_serv_list['file1'][0]),
      }
      
db_web = cli['web']['zakka']
db_web.authenticate('ipcam','ipcam')

#db_file1 = cli['file1']['zakka']
#db_file1.authenticate('ipcam','ipcam')

#tmp_path = '/usr/local/nginx/html/ipcam_ws/static/tmp'
logs_path = '/usr/local/nginx/logs'
snap_store_path = '/data'
http_port=80
https_port=443

mail_server='127.0.0.1'
sender='"zakka"<zakka@f8geek.com>'

web.config.debug = debug_mode

config = web.storage(
    email = 'jack139@gmail.com',
    site_name = 'ipcam',
    site_des = '',
    static = '/static'
)
