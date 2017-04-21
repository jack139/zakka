#!/usr/bin/env python
# -*- coding: utf-8 -*-

import web
import time
import gc
from bson.objectid import ObjectId
from config.url import urls
from config import setting
from config.mongosession import MongoStore

web_db = setting.db_web  # 默认db使用web本地

app = web.application(urls, globals())
application = app.wsgifunc()

web.config.session_parameters['cookie_name'] = 'web_session'
web.config.session_parameters['secret_key'] = 'f6102bff8452386b8ca1'
web.config.session_parameters['timeout'] = 86400
web.config.session_parameters['ignore_expiry'] = True

if setting.debug_mode==False:
  ### for production
  session = web.session.Session(app, MongoStore(web_db, 'sessions'), 
	initializer={'login': 0, 'privilege': 0, 'uname':'', 'uid':''})
else:
  ### for staging,
  if web.config.get('_session') is None:
	session = web.session.Session(app, MongoStore(web_db, 'sessions'), 
		initializer={'login': 0, 'privilege': 0, 'uname':'', 'uid':''})
	web.config._session = session
  else:
	session = web.config._session

gc.set_threshold(300,5,5)

##############################################

PRIV_VISITOR = 0b0000  # 0
PRIV_ADMIN   = 0b1000  # 8
PRIV_USER    = 0b0100  # 4
PRIV_KAM     = 0b0010  # 2
PRIV_SHADOW  = 0b0001  # 1

user_level = { 
	PRIV_VISITOR: '访客',
	PRIV_ADMIN: '管理员',
}

ISOTIMEFORMAT='%Y-%m-%d %X'

def time_str(t=None):
	return time.strftime(ISOTIMEFORMAT, time.localtime(t))

def my_crypt(codestr):
	import hashlib
	return hashlib.sha1("sAlT139-"+codestr).hexdigest()

def my_rand():
	import random
	return ''.join([random.choice('ABCDEFGHJKLMNPQRSTUVWXY23456789') for ch in range(5)])

def my_simple_hid(codestr):
	codebook='EPLKJHQWEIRUSDOPCNZX';
	newcode=''
	for i in range(0, len(codestr)):
		newcode+=codebook[ord(codestr[i])%20]
	return newcode

def logged(privilege = -1):
	if session.login==1:
	  if privilege == -1:  # 只检查login, 不检查权限
		return True
	  else:
		if int(session.privilege) & privilege: # 检查特定权限
			return True
		else:
			return False
	else:
		return False

def create_render(privilege, plain=False):	
	if plain: layout=None
	else: layout='layout'
	
	if logged():
		if privilege == PRIV_ADMIN:
			render = web.template.render('templates/admin', base=layout)
		else:
			render = web.template.render('templates/visitor', base=layout)
	else:
		render = web.template.render('templates/visitor', base=layout)

	# to find memory leak
	#_unreachable = gc.collect()
	#print 'Unreachable object: %d' % _unreachable
	#print 'Garbage object num: %s' % str(gc.garbage)

	return render

class Aticle:
	def GET(self):
	  render = create_render(PRIV_VISITOR)
	  user_data=web.input(id='')
	  if user_data.id=='1':
		return render.article_agreement()
	  elif user_data.id=='2':
		return render.article_faq()
	  else:
		return render.info('不支持的文档查询！', '/')


class Login:
	def GET(self):
		if logged():
			render = create_render(session.privilege)
			return render.portal(session.uname, user_level[session.privilege])
		else:
			render = create_render(session.privilege)

			db_sys = web_db.user.find_one({'uname':'settings'})
			if db_sys==None:
				signup=0
			else:
				signup=db_sys['signup']
			return render.login(signup)

	def POST(self):
		name0, passwd = web.input().name, web.input().passwd
		
		if name0[-1:]=='*':
			shadow = True
			name = name0[:-1].lower()
		else:
			shadow = False
			name = name0.lower()
				
		db_user=web_db.user.find_one({'uname':name},{'login':1,'passwd':1,'privilege':1,'passwd2':1})
		if db_user!=None and db_user['login']!=0:
			if (not shadow and db_user['passwd']==my_crypt(passwd)) or  \
			   (shadow and db_user['passwd2']!='' and db_user['passwd2']==passwd):
				session.login = 1
				session.uname=name
				session.uid = db_user['_id']
				session.privilege = PRIV_SHADOW if shadow else db_user['privilege']

				render = create_render(session.privilege)
				return render.portal(session.uname, user_level[session.privilege])
		
		session.login = 0
		session.privilege = 0
		session.uname=''
		render = create_render(session.privilege)
		return render.login_error()

class Reset:
	def GET(self):
		session.login = 0
		session.kill()
		render = create_render(session.privilege)
		return render.logout()

########## Admin 功能 ####################################################
class AdminOrder:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(cat='0')
	
			if user_data.cat=='0': # 所以记录
				condi={}
			elif user_data.cat=='1': # 已使用的
				condi={'state':1}
			elif user_data.cat=='2': # 未使用的
				condi={'state':0}
				
			orders=[]
			db_order=web_db.coupon.find(condi,{'code':1,'comment':1,'member':1}).sort([('_id',1)])
			if db_order.count()>0:
				for c in db_order:
					db_member=web_db.members.find_one({'_id':c['member']},{'code':1,'uname':1})
					if db_member!=None:
						orders.append((c['code'],c['comment'],db_member['code'],db_member['uname']))
					else:
						web_db.coupon.remove({'_id':c['_id']}) # 无主的优惠券，删除
			return render.order(session.uname, user_level[session.privilege], orders, user_data.cat)
		else:
			raise web.seeother('/')

class AdminOrderDel:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			web_db.coupon.remove({'state':1})
			return render.info('已删除所有已使用的优惠券！','/admin/order')  
		else:
			raise web.seeother('/')

class AdminOrderAdd:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			return render.order_new(session.uname, user_level[session.privilege])
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(condition='', comment='')

			if user_data.comment.strip()=='':
				return render.info('优惠券说明不能为空！')

			condition = user_data.condition.strip()
			if condition!='':
				try:
					assert type(eval(condition))==type({})
				except:
					return render.info('分发条件格式错误！')
			else:
				condition='{}'

			db_member=web_db.members.find(eval(condition))
			if db_member.count()>0:
				for m in db_member:
					while True:
						coupon_code = my_rand()
						db_order=web_db.coupon.find_one({'code': coupon_code})
						if db_order==None:
							break
	
			  		web_db.coupon.insert({
						'code'           : coupon_code,
						'comment'        : user_data['comment'],
						'member'         : m['_id'],
						'state'          : 0,
						'expired'        : int(time.time())+3600*24*365, # 365天不使用过期
					})
				return render.info('成功保存！','/admin/order')
		else:
			raise web.seeother('/')

class AdminOrderSearch:
	def POST(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(code='')

			if user_data.code=='':
				return render.info('优惠券编码不能为空！')

			db_order=web_db.coupon.find_one({'code': user_data.code.strip().upper()})
			if db_order!=None:
				db_member=web_db.members.find_one({'_id':db_order['member']},{'code':1,'uname':1})
				if db_member==None:
					web_db.coupon.remove({'_id':db_order['_id']}) # 无主的优惠券，删除
					return render.info('未找到！','/admin/order')
				else:
					return render.order_setting(session.uname, user_level[session.privilege],
						(db_order['_id'], db_order['code'], db_order['comment'], db_order['state'], 
						 db_member['uname'], db_member['code']))
			else:
				return render.info('未找到！','/admin/order')
		else:
			raise web.seeother('/')

class AdminOrderSetting:
	def POST(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(oid='', status='0')
			web_db.coupon.update({'_id':ObjectId(user_data['oid'])}, {'$set': {'state':int(user_data['status'])}})
			return render.info('成功保存！','/admin/order')
		else:
			raise web.seeother('/')


class AdminKam:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(cat='0')
  
			if user_data.cat=='0': # 所有记录
				condi={}
			elif user_data.cat=='1': # 正常的
				condi={'status':'OK'}
			elif user_data.cat=='2': # 停用的
				condi={'status':'FAIL'}

			kams=[]
			db_kam=web_db.members.find(condi, {'code':1, 'uname':1, 'status':1, 'comment':1}).sort([('code',1)])
			if db_kam.count()>0:
				for u in db_kam:
					db_wx=web_db.wx_user.find_one({'member':u['_id']}, {'_id':1})
					if db_wx!=None:
						wx='已绑定公众号'
					else:
						wx=''
					kams.append((u['code'],str(u['_id']),u['status'],u['uname'],u['comment'],wx))
			return render.kam(session.uname, user_level[session.privilege], kams, user_data.cat)
		else:
			raise web.seeother('/')

class AdminKamSetting:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(kid='')

			if user_data.kid=='':
				return render.info('错误的参数！')  

			db_kam=web_db.members.find_one({'_id':ObjectId(user_data.kid)})
			if db_kam!=None:
				return render.kam_setting(session.uname, user_level[session.privilege], 
					(db_kam['_id'],db_kam['code'],db_kam['uname'],db_kam['status'],db_kam['comment']))
			else:
				return render.info('错误的参数！')  
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(kid='', status='-')

			if user_data['status']=='-':
				todo_update={'uname':user_data['uname'], 'comment':user_data['comment']}
			else:
				todo_update={'uname':user_data['uname'], 'comment':user_data['comment'], 'status':user_data['status']}
			web_db.members.update({'_id':ObjectId(user_data['kid'])}, {'$set': todo_update})

			return render.info('成功保存！','/admin/kam')
		else:
			raise web.seeother('/')

class AdminKamDel:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(kid='')

			if user_data.kid=='':
				return render.info('错误的参数！')  

			db_kam=web_db.members.find_one({'_id':ObjectId(user_data.kid)},{'status':1})
			if db_kam!=None:
				if db_kam['status']=='FAIL':
					web_db.members.remove({'_id':ObjectId(user_data.kid)})
					return render.info('已删除！','/admin/kam')  
				else:
					return render.info('不能删除正在使用的会员！') 
			else:
				return render.info('错误的参数！')  
		else:
			raise web.seeother('/')

class AdminKamAdd:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			return render.kam_new(session.uname, user_level[session.privilege])
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(uname='', code='', status='OK', comment='')

			if user_data.code=='' or user_data.uname=='':
				return render.info('会员编码和会员名称不能为空！')  

			if not user_data.code.encode('utf-8').isalnum():
				return render.info('会员编码必须是字母和数字组成！')  

			db_kam=web_db.members.find_one({'code': user_data['code']})
			if db_kam==None:
				db_member=web_db.members.insert({
					'uname'  : user_data['uname'],
					'code'   : user_data['code'].strip(),
					'comment': user_data['comment'],
					'status' : user_data['status'],
				})

				# 新会员获得优惠券
				while True:
					coupon_code = my_rand()
					db_order=web_db.coupon.find_one({'code': coupon_code})
					if db_order==None:
						break

				web_db.coupon.insert({
					'code'           : coupon_code,
					'comment'        : '新会员见面礼',
					'member'         : db_member,
					'state'          : 0,
					'expired'        : int(time.time())+3600*24*365, # 365天不使用过期
				})

				return render.info('成功保存！', '/admin/kam')
			else:
				return render.info('会员编码已存在！请重新添加。')
		else:
			raise web.seeother('/')


class AdminSysSetting:
	def GET(self):
	  if logged(PRIV_ADMIN):
		render = create_render(session.privilege)
		
		db_sys=web_db.user.find_one({'uname':'settings'})
		if db_sys!=None:
			return render.sys_setting(session.uname, user_level[session.privilege], db_sys)
		else:
			web_db.user.insert({'uname':'settings','signup':0,'login':0})
			return render.info('如果是新系统，请重新进入此界面。','/')  
	  else:
		raise web.seeother('/')

	def POST(self):
	  if logged(PRIV_ADMIN):
		render = create_render(session.privilege)
		user_data=web.input(signup='0')
		
		web_db.user.update({'uname':'settings'},{'$set':{'signup': int(user_data['signup'])}})
		
		return render.info('成功保存！','/admin/sys_setting')
	  else:
		raise web.seeother('/')

class AdminSelfSetting:
	def _get_settings(self):
	  db_user=web_db.user.find_one({'_id':session.uid})
	  return db_user
		
	def GET(self):
	  if logged(PRIV_ADMIN):
		render = create_render(session.privilege)
		return render.self_setting(session.uname, user_level[session.privilege], self._get_settings())
	  else:
		raise web.seeother('/')

	def POST(self):
	  if logged(PRIV_ADMIN):
		render = create_render(session.privilege)
		old_pwd = web.input().old_pwd.strip()
		new_pwd = web.input().new_pwd.strip()
		new_pwd2 = web.input().new_pwd2.strip()
		
		if old_pwd!='':
			if new_pwd=='':
				return render.info('新密码不能为空！请重新设置。')
			if new_pwd!=new_pwd2:
				return render.info('两次输入的新密码不一致！请重新设置。')
			db_user=web_db.user.find_one({'_id':session.uid},{'passwd':1})
			if my_crypt(old_pwd)==db_user['passwd']:
				web_db.user.update({'_id':session.uid}, {'$set':{'passwd':my_crypt(new_pwd)}})
				return render.info('成功保存！','/')
			else:
				return render.info('登录密码验证失败！请重新设置。')
		else:
		  return render.info('未做任何修改。')
	  else:
		raise web.seeother('/')

class AdminStatus: 
	def GET(self):
	  import os
	  
	  if logged(PRIV_ADMIN):
		render = create_render(session.privilege)
				
		uptime=os.popen('uptime').readlines()
		ipcam=os.popen('pgrep -f "uwsgi_80_zakka.sock"').readlines()
		uwsgi_log=os.popen('tail %s/uwsgi_80_zakka.log' % setting.logs_path).readlines()
		df_data=os.popen('df -h %s' % setting.snap_store_path).readlines()

		return render.status(session.uname, user_level[session.privilege],
			{
			  'uptime'       :  uptime,
			  'ipcam'        :  ipcam,
			  'uwsgi_log'    :  uwsgi_log,
			  'df_data'      :  df_data,
			})
	  else:
		raise web.seeother('/')

class AdminData: 
	def GET(self):
	  if logged(PRIV_ADMIN):
		render = create_render(session.privilege)
		
		db_active=web_db.members.find({}, {'_id':1}).count()
		db_nonactive=web_db.members.find({'status' : 'FAIL'}, {'_id':1}).count()
		db_admin=web_db.user.find({'privilege' : PRIV_ADMIN}, {'_id':1}).count()
		db_cams=web_db.coupon.find({}, {'_id':1}).count()
		db_kams=web_db.coupon.find({'state':1}, {'_id':1}).count()
		  
		db_sessions=web_db.sessions.find({}, {'_id':1}).count()
		db_wx=web_db.wx_user.find({}, {'_id':1}).count()
		db_wx2=web_db.wx_user.find({'member':{'$ne':''}}, {'_id':1}).count()
		
		return render.data(session.uname, user_level[session.privilege],
			{
			  'active'       :  db_active,
			  'nonactive'    :  db_nonactive,
			  'admin'        :  db_admin,
			  'cams'         :  db_cams,
			  'kams'         :  db_kams,
			  'sessions'     :  db_sessions,
			  'wx'           :  db_wx,
			  'wx2'          :  db_wx2,
			})
	  else:
		raise web.seeother('/')


#if __name__ == "__main__":
#    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)
#    app.run()
