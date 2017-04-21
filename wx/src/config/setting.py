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

http_port=80
https_port=443

wx_appid='wx1d2f4c97c33b8f87'
wx_secret='47c07dfd246417d76ed3a213148e44c0'

web.config.debug = debug_mode

config = web.storage(
    email = 'jack139@gmail.com',
    site_name = 'wx',
    site_des = '',
    static = '/static'
)
