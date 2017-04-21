#!/usr/bin/env python
# -*- coding: utf-8 -*-

import web
import time
import gc
from bson.objectid import ObjectId
from config.url import urls
from config import setting
#from config.mongosession import MongoStore
#import helper
#from helper import time_str
try:
	import xml.etree.cElementTree as ET
except ImportError:
	import xml.etree.ElementTree as ET

web_db = setting.db_web  # 默认db使用web本地
#file_db = setting.db_file1

app = web.application(urls, globals())
application = app.wsgifunc()

gc.set_threshold(300,5,5)

##############################################

PRIV_VISITOR = 0b0000  # 0
PRIV_ADMIN   = 0b1000  # 8
PRIV_USER    = 0b0100  # 4

ISOTIMEFORMAT='%Y-%m-%d %X'

def time_str(t=None):
    return time.strftime(ISOTIMEFORMAT, time.localtime(t))

def my_crypt(codestr):
	import hashlib
	return hashlib.sha1("sAlT139-"+codestr).hexdigest()

def my_rand():
	import random
	return ''.join([random.choice('ABCDEFGHJKLMNPQRSTUVWXY23456789') for ch in range(8)])

def my_simple_hid(codestr):
	codebook='EPLKJHQWEIRUSDOPCNZX';
	newcode=''
	for i in range(0, len(codestr)):
		newcode+=codebook[ord(codestr[i])%20]
	return newcode

def create_render(plain=False):    
	if plain: layout=None
	else: layout='layout'
	render = web.template.render('templates/visitor', base=layout)
	return render

def check_wx_user(wx_user):
	db_wx=web_db.wx_user.find_one({'wx_user':wx_user},{'member':1})
	if db_wx!=None: # 已登记
		return db_wx['member']
	else: # 未登记
		web_db.wx_user.insert({'wx_user' : wx_user, 'member': '', 'admin':'', 'time' : time_str()})
		return ''

def bind_wx_user(wx_user, member=''):
	check_wx_user(wx_user)
	web_db.wx_user.update({'wx_user':wx_user},{'$set': {'member':member}})

def check_wx_admin(wx_user):
	db_wx=web_db.wx_user.find_one({'wx_user':wx_user},{'admin':1})
	if db_wx!=None: # 已登记
		return db_wx['admin']
	else: # 未登记
		return ''

def bind_wx_admin(wx_user, admin=''):
	check_wx_user(wx_user)
	web_db.wx_user.update({'wx_user':wx_user},{'$set': {'admin':admin}})

def reply_none():
	web.header("Content-Type", "text/plain") # Set the Header
	return ""

class PostMsg:
	def __init__(self, str_xml):
		self.xml=ET.fromstring(str_xml)
		self.fromUser=self.xml.find("FromUserName").text
		self.toUser=self.xml.find("ToUserName").text
		self.msgType=self.xml.find("MsgType").text
		self.key=''
	
	def reply_text(self, content):
		render = create_render(plain=True)
		return render.xml_reply(self.fromUser, self.toUser, int(time.time()), content)

	def reply_media(self, content):
		# 标题，说明，图片url，页面url
		#content = [(u'标题2', u'', u'', u'http://wx.f8geek.com/live2')]
		render = create_render(plain=True)
		return render.xml_media(self.fromUser, self.toUser, int(time.time()), content)		

	def text_process(self): # 处理文本消息回复
		content=self.xml.find("Content").text
		cmd0 = content.split()
		tick=str(int(time.time()))
		hid=my_crypt('%s%s' % (self.fromUser,tick))
		if cmd0[0].lower()=='login':
			return self.reply_media([(u'请点击如下操作：',u'',u'',u''),
				(u'管理员登录',u'',u'http://zkwx.f8geek.com/static/finger.jpg',
				 u'http://zkwx.f8geek.com/login?wxuid=%s&tick=%s&hid=%s' % \
					(self.fromUser, tick, hid))
			])
		elif cmd0[0].lower()==u'admin':
			admin=check_wx_admin(self.fromUser)
			if admin!='':
				return self.reply_media([
					(u'点击选择功能',u'',u'',u''),
					(u'管理优惠券',u'',u'http://zkwx.f8geek.com/static/coupon.png',
					 u'http://zkwx.f8geek.com/coupon?wxuid=%s&tick=%s&hid=%s' % \
						(self.fromUser, tick, hid))
				])
			else:
				return self.reply_text( u"无管理员权限！")
		elif cmd0[0].lower()=='logout':
			bind_wx_admin(self.fromUser)
			return self.reply_text( u"已退出管理员登录。")
		#elif cmd0[0].lower()=='test':
		#	return self.reply_media([(u'标题',u'描述',u'',u''),
		#		(u'标题2',u'描述2',u'',u'')])
		elif cmd0[0].lower()==u'自助':
			return self.reply_media([
				(u'点击选择自助服务',u'',u'',u''),
				(u'我的优惠券',u'',u'http://zkwx.f8geek.com/static/sale.png',
				 u'http://zkwx.f8geek.com/my_coupon?wxuid=%s&tick=%s&hid=%s' % \
						(self.fromUser, tick, hid)),
				(u'Zakka-sale 微店',u'',u'http://zkwx.f8geek.com/static/weidian.png',
				 u'http://weidian.com/s/313000690?wfr=c'),
				(u'Zakka-sale 淘宝店',u'',u'http://zkwx.f8geek.com/static/taobao.jpg',
				 u'http://zakka-sale.taobao.com'),
				 #u'http://zkwx.f8geek.com/static/taobao.html'),
				(u'实体店信息',u'',u'http://zkwx.f8geek.com/static/shop.png',
				 u'http://zkwx.f8geek.com/contact')
			])
		else:
			db_user=web_db.members.find_one({'code':cmd0[0]},{'status':1,'uname':1})
			if db_user!=None and db_user['status']=='OK':
				bind_wx_user(self.fromUser, db_user['_id'])
				return self.reply_text( u"%s，您已成功绑定ZAKKA-SALE会员！" \
						u"您现在可以发送“自助”使用自助服务了。" % db_user['uname'])
			else:
				return self.reply_text( u"未能识别您发送的内容。" \
						u"发送如下内容可以进行自助操作：\n" \
					 	u"1.发送“自助”查看自助服务内容\n" \
					 	u"2.发送会员编号绑定会员身份，将获得更多优惠" )

	def event_process(self): # 处理事件请求
		event=self.xml.find("Event").text
		if event=='CLICK': # 订阅号不没有菜单请求
			self.key=self.xml.find("EventKey").text
			if self.key=='NEWS_FREE':
				return self.reply_text(u"免费试用项目：\n1.305标清相机；\n2.安卓应用Kam4A。")
		elif event=='subscribe':
			#print "NEW: %s" % self.fromUser
			bind_wx_user(self.fromUser, '')
			return self.reply_text(u"谢谢您关注ZAKKA-SALE微信公众号！" \
				u"发送如下内容可以完成自助操作:\n" \
				u"1.发送“自助”查看自助服务内容\n" \
				u"2.发送会员编号绑定会员身份，将获得更多优惠" )
		elif event=='unsubscribe':
			#print "LEFT: %s" % self.fromUser
			bind_wx_user(self.fromUser)
		return reply_none()

	def do_process(self):
		if self.msgType=='text':
			return self.text_process()
		elif self.msgType=='event':
			return self.event_process()
		else:
			return reply_none()

class First:
	def GET(self):
		import hashlib
		user_data=web.input(signature='', timestamp='', nonce='', echostr='')
		if '' in (user_data.signature, user_data.timestamp, user_data.nonce, user_data.echostr):
			return reply_none()

		token1='7a710d7955acb49fbf1a'  # hashlib.sha1('ilovekam').hexdigest()[5:25]
		tmp=[token1, user_data.timestamp, user_data.nonce]
		tmp.sort()
		tmp1=tmp[0]+tmp[1]+tmp[2]
		tmp2=hashlib.sha1(tmp1).hexdigest()
		#print "%s %s %s" % (tmp1, tmp2, user_data.signature)
		
		web.header("Content-Type", "text/plain") # Set the Header
		if tmp2==user_data.signature:
			return user_data.echostr
		else:
			return "fail!"

	def POST(self):
		import hashlib
		user_data=web.input(signature='', timestamp='', nonce='')
		if '' in (user_data.signature, user_data.timestamp, user_data.nonce):
			return reply_none()
		
		token1='7a710d7955acb49fbf1a'  # hashlib.sha1('ilovekam').hexdigest()[5:25]
		tmp=[token1, user_data.timestamp, user_data.nonce]
		tmp.sort()
		tmp1=tmp[0]+tmp[1]+tmp[2]
		tmp2=hashlib.sha1(tmp1).hexdigest()

		if tmp2!=user_data.signature:
			return reply_none()

		#从获取的xml构造xml dom树
		str_xml=web.data()
		
		#print str_xml
		
		pm=PostMsg(str_xml)
		return pm.do_process()

class Login:
	def GET(self):
		render = create_render()
		user_data=web.input(wxuid='', tick='', hid='')

		if '' in (user_data.wxuid, user_data.tick, user_data.hid):
			return render.info('未授权的访问！(101)')

		if time.time()-int(user_data.tick)>3600: # HID 过期
			return render.info('未授权的访问！(102)')

		if my_crypt('%s%s' % (user_data.wxuid,user_data.tick))!=user_data.hid:
			return render.info('未授权的访问！(103)')

		return render.login(user_data.wxuid, user_data.tick, user_data.hid)

	def POST(self):
		render = create_render()
		user_data=web.input(wxuid='', tick='', hid='', name='', passwd='')
		name0, passwd = user_data.name, user_data.passwd

		if '' in (user_data.wxuid, user_data.tick, user_data.hid):
			return render.info('未授权的访问！(101)')

		if time.time()-int(user_data.tick)>3600: # HID 过期
			return render.info('未授权的访问！(102)')

		if my_crypt('%s%s' % (user_data.wxuid,user_data.tick))!=user_data.hid:
			return render.info('未授权的访问！(103)')

		if name0=='':
			return render.info('用户名不能为空！')

		name = name0.lower()

		db_user=web_db.user.find_one({'uname':name},{'login':1,'passwd':1,'privilege':1})
		if db_user!=None and db_user['login']!=0 and db_user['privilege']==PRIV_ADMIN:
			if db_user['passwd']==my_crypt(passwd):
				bind_wx_admin(user_data.wxuid, db_user['_id'])
				return render.info("已成功绑定管理员用户！" \
					"请先关闭此窗口，然后发送admin使用管理功能。")
			else:
				return render.info("密码错误！")
		else:
			return render.info("未找到用户")


class Coupon:
	def GET(self):
		render = create_render()
		user_data=web.input(wxuid='', tick='', hid='')

		if '' in (user_data.wxuid, user_data.tick, user_data.hid):
			return render.info('未授权的访问！(101)')

		if time.time()-int(user_data.tick)>3600: # HID 过期
			return render.info('未授权的访问！(102)')

		if my_crypt('%s%s' % (user_data.wxuid,user_data.tick))!=user_data.hid:
			return render.info('未授权的访问！(103)')

		return render.coupon(user_data.wxuid, user_data.tick, user_data.hid)

	def POST(self):
		render = create_render()
		user_data=web.input(wxuid='', tick='', hid='', code='')
		code0 = user_data.code

		if '' in (user_data.wxuid, user_data.tick, user_data.hid):
			return render.info('未授权的访问！(101)')

		if time.time()-int(user_data.tick)>3600: # HID 过期
			return render.info('未授权的访问！(102)')

		if my_crypt('%s%s' % (user_data.wxuid,user_data.tick))!=user_data.hid:
			return render.info('未授权的访问！(103)')

		if code0=='':
			return render.info('优惠券编号不能为空！')

		code1=code0.strip().upper()

		db_coupon=web_db.coupon.find_one({'code':code1},{'comment':1,'member':1,'state':1})
		if db_coupon!=None:
			db_member=web_db.members.find_one({'_id':db_coupon['member']},{'uname':1,'code':1,'status':1})
			if db_member!=None:
				if db_member['status']!='OK':
					return render.info("此优惠券的会员已被停用，优惠券无效！")
			else:
				return render.info("未找到优惠券的会员，优惠券无效！。")

			return render.coupon_check(user_data.wxuid, user_data.tick, user_data.hid, 
				(db_member['code'],db_member['uname']), 
				(code1, db_coupon['comment'], db_coupon['state'], code1) )
		else:
			return render.info("未找到优惠券！")

class CouponUse:
	def POST(self):
		render = create_render()
		user_data=web.input(wxuid='', tick='', hid='', code='')
		code0 = user_data.code

		if '' in (user_data.wxuid, user_data.tick, user_data.hid):
			return render.info('未授权的访问！(101)')

		if time.time()-int(user_data.tick)>3600: # HID 过期
			return render.info('未授权的访问！(102)')

		if my_crypt('%s%s' % (user_data.wxuid,user_data.tick))!=user_data.hid:
			return render.info('未授权的访问！(103)')

		if code0=='':
			return render.info('优惠券编号不能为空！')

		code1=code0.upper()

		db_coupon=web_db.coupon.find_one({'code':code1},{'comment':1,'member':1,'state':1})
		if db_coupon!=None:
			if db_coupon['state']==0:
				web_db.coupon.update({'code':code1},{'$set':{'state':1}})
				return render.info(u"<%s - %s> 有效。成功使用此优惠券，此优惠券状态已变更为“已使用”。" 
					% (code1,db_coupon['comment']))
			else:
				return render.info(u"<%s - %s> 不可用。使用此优惠券失败！。"
					% (code1,db_coupon['comment']))
		else:
			return render.info("未找到优惠券！")

class MyCoupon:
	def GET(self):
		render = create_render()
		user_data=web.input(wxuid='', tick='', hid='')

		if '' in (user_data.wxuid, user_data.tick, user_data.hid):
			return render.info('此次会话已过期，请重新发送‘自助’！(101)')

		if time.time()-int(user_data.tick)>3600: # HID 过期
			return render.info('此次会话已过期，请重新发送‘自助’！(102)')

		if my_crypt('%s%s' % (user_data.wxuid,user_data.tick))!=user_data.hid:
			return render.info('此次会话已过期，请重新发送‘自助’！(103)')

		member=check_wx_user(user_data.wxuid)

		coupons=[]
		if member=='':
			return render.mycoupon('非会员', coupons, "请先绑定会员身份。")

		db_member=web_db.members.find_one({'_id':member},{'uname':1,'status':1})
		if db_member!=None:
			if db_member['status']!='OK':
				render.mycoupon(db_member['uname'], coupons, "抱歉！您的会员资格已停用，请联系客服人员。")
		else:
			bind_wx_user(user_data.wxuid)
			return render.mycoupon('非会员', coupons, "抱歉！您的会员身份验证失败，请发送会员编码重新绑定会员身份。")

		msg=''
		db_coupon=web_db.coupon.find({'member':member},{'code':1,'comment':1,'state':1})
		if db_coupon.count()>0:
			for c in db_coupon:
				coupons.append((c['code'], c['comment'], c['state']))
		else:
			msg='您还没有优惠卷，请持续关注我们的优惠活动。'
		return render.mycoupon(db_member['uname'], coupons, msg)

class Contact:
	def GET(self):
		render = create_render()
		return render.contact()

#if __name__ == "__main__":
#    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)
#    app.run()
