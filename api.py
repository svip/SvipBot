# encoding: utf-8

import urllib2, urllib
from xml.dom.minidom import parseString
import gzip,StringIO
import httplib,socket

class Api(object):
	server = "theinfosphere.org"
	url = "http://theinfosphere.org/api.php"
	indexurl = "http://theinfosphere.org/index.php"
	default_data = {"format" : "xml"}
	user_data = {}
	logged_in = False
	send_cookies = False
	debugmode = False
	additional_cookies = {}
	httpsocket = None
	
	def init_socket(self):
		self.httpsocket = httplib.HTTPConnection(self.server, 80)
	
	def getresponse(self, method, url, query, headers, limit=1):
		if limit > 5:
			return None
		try:
			if method == 'POST':
				self.httpsocket.request(method, url, query, headers)
			else:
				self.httpsocket.request(method, url+'?'+query, '', headers)				
			response = self.httpsocket.getresponse()
		except httplib.BadStatusLine:
			return None
		except socket.error:
			self.httpsocket.close()
			self.httpsocket.connect()
			response = self.getresponse(method, url, query, headers, limit+1)
		except httplib.CannotSendRequest:
			self.httpsocket.close()
			self.httpsocket.connect()
			response = self.getresponse(method, url, query, headers, limit+1)
		return response

	def post(self, data, tries=1):
		if tries > 5:
			return None
		orgdata = data
		data.update(self.default_data)
		query = []
		for d in data:
			query.append('='.join((d, urllib.quote(unicode(data[d]).encode('utf-8')))))
		query = '&'.join(query)
		if self.debugmode:
			print query
		headers = {"Accept-encoding" : "gzip", 'Content-type': 'application/x-www-form-urlencoded'}
		if self.send_cookies:
			headers.update({"Cookie" : self.make_cookie()})
		if data['action']=='edit':
			headers.update({"Content-Type" : "application/x-www-form-urlencoded"})
		if self.httpsocket is None:
			self.init_socket()
		try:
			self.httpsocket.connect()
		except socket.error:
			return self.post(orgdata, tries+1)
		response = self.getresponse("POST", "/api.php", query, headers)
		if response is None:
			return None
		setcookie = response.getheader('Set-Cookie')
		if not setcookie is None:
			cookie = setcookie.split(";")[0].split("=")
			self.additional_cookies.update({cookie[0] : cookie[1]})
		compressedstream = StringIO.StringIO(response.read())
		gzipper = gzip.GzipFile(fileobj=compressedstream)
		self.httpsocket.close()
		return gzipper.read()
	
	def index_request(self, title, action, query={}):
		data = {"title" : title, "action" : action}
		data.update(query)
		query = []
		for d in data:
			query.append('='.join((d, urllib.quote(data[d]))))
		query = '&'.join(query)
		headers = {"Accept-encoding" : "gzip"}
		try:
			if self.httpsocket is None:
				self.init_socket()
			if self.debugmode:
				print query
			response = self.getresponse("GET", "/index.php", query, headers)
			if response is None:
				return None
			raw = response.read()
			compressedstream = StringIO.StringIO(raw)
			gzipper = gzip.GzipFile(fileobj=compressedstream)
			return gzipper.read().decode("utf8")
		except IOError:
			return raw
	
	def make_cookie(self):
		p = self.user_data["cookieprefix"]
		if self.logged_in:
			cookie = {p + "UserName" : self.user_data["username"],
				p + "UserID" : self.user_data["userid"],
				p + "Token" : self.user_data["token"],
				p + "_session" : self.user_data["sessionid"]}
		else:
			cookie= {p + "_session" : self.user_data["sessionid"]}
		cookie.update(self.additional_cookies)
		line = ""
		for c in cookie:
			if line!="":
				line += "; "
			line += c + "=" + cookie[c]
		return line
	
	def create_page(self, title, content, summary="Bot edit"):
		query = {"action" : "query", "prop" : "info|revisions", "intoken" : "edit", "titles" : title}
		xml = parseString(self.post(query))
		try:
			t = xml.getElementsByTagName("revisions")[0]
			return False
		except IndexError:
			pass
		token = xml.getElementsByTagName("page")[0].attributes["edittoken"].value
		query = {"action" : "edit", "title" : title, "text" : content, "bot" : "true",
		"createonly" : "true", "summary" : summary, "token" : token}
		if self.debugmode:
			return False
		t = self.post(query)
		if t == None:
			return False
		xml = parseString(t)
		try:
			edit = xml.getElementsByTagName("edit")[0]
			if edit.attributes["result"].value=="Success":
				return True
		except KeyError:
			error = xml.getElementsByTagName("error")[0]
			if error.attributes["code"].value == "articleexists":
				return False
		return False
	
	def edit_page(self, title, content, summary="Bot edit", section=None):
		query = {"action" : "query", "prop" : "info|revisions", "intoken" : "edit", "titles" : title}
		t = self.post(query)
		if t == None:
			return False
		xml = parseString(t)
		token = xml.getElementsByTagName("page")[0].attributes["edittoken"].value
		query = {"action" : "edit", "title" : title, "text" : content, "bot" : "true", "summary" : summary, "token" : token}
		if section!=None:
			query.update({"section" : str(section)})
		if self.debugmode:
			return False
		t = self.post(query)
		if t == None:
			return False
		xml = parseString(t)
		return True
	
	def delete_page(self, title, reason="Bot deletion"):
		query = {"action" : "query", "prop" : "info|revisions", "intoken" : "delete", "titles" : title}
		xml = parseString(self.post(query))
		token = xml.getElementsByTagName("page")[0].attributes["deletetoken"].value
		query = {"action" : "delete", "title" : title, "reason" : reason, "token" : token}
		if self.debugmode:
			return False
		t = self.post(query)
		if t == None:
			return False
		xml = parseString(t)
		return True
	
	def block_user(self, user, expiry, reason="Bot blockage"):
		query = {"action" : "block", "gettoken" : "yes", "user" : user}
		xml = parseString(self.post(query))
		token = xml.getElementsByTagName("block")[0].attributes["blocktoken"].value
		query = {"action" : "block", "user" : user, "expiry" : expiry, "reason" : reason, "token" : token}
		if self.debugmode:
			return False
		t = self.post(query)
		if t == None:
			return False
		return True
	
	def get_token(self, title, tokentype='edit'):
		query = {'action' : 'query', 'prop' : 'info|revisions', 'intoken' : tokentype, 'titles' : title}
		xml = parseString(self.post(query))
		token = xml.getElementsByTagName('page')[0].attributes["%stoken"%tokentype].value
		return token
	
	def move(self, old, new, summary="Bot edit"):
		token = self.get_token(old, 'move')
		query = {'action' : 'move', 'from' : old, 'to' : new,
				'token' : token, 'movetalk' : 'true', 'reason' : summary}
		if self.debugmode:
			return False
		t = self.post(query)
		if t == None:
			return False
		xml = parseString(t)
		return True
	
	def login(self, username, password):
		query = {"action" : "login", "lgname" : username, "lgpassword" : password}
		t = self.post(query)
		xml = parseString(t)
		login = xml.getElementsByTagName("login")[0]
		a = login.attributes
		if a['result'].value == 'NeedToken':
			cookieprefix = a["cookieprefix"].value
			sessionid = a["sessionid"].value
			self.user_data.update({"cookieprefix" : cookieprefix, 
				"sessionid" : sessionid})
			self.send_cookies = True
		token = a['token'].value
		query = {"action" : "login", "lgname" : username, 
				"lgpassword" : password, "lgtoken" : token}
		t = self.post(query)
		if t == None:
			return False
		xml = parseString(t)
		login = xml.getElementsByTagName("login")[0]
		a = login.attributes
		i = 1
		while a['result'].value == 'NeedToken':
			# keep trying
			sessionid = a["sessionid"].value
			self.user_data.update({	"sessionid" : sessionid})
			token = a['token'].value
			query = {"action" : "login", "lgname" : username, 
				"lgpassword" : password, "lgtoken" : token}
			t = self.post(query)
			print t
			if t == None:
				return False
			xml = parseString(t)
			login = xml.getElementsByTagName("login")[0]
			a = login.attributes	
			i += 1
			if i > 9:
				return False
		try:
			login = xml.getElementsByTagName("login")[0]
		except IndexError:
			return False
		a = login.attributes
		if a["result"].value == "Success":
			userid = a["lguserid"].value
			username = a["lgusername"].value
			token = a["lgtoken"].value
			self.user_data.update({"userid" : userid, "username" : username,
					"token" : token})
			self.logged_in = True
			return True
		return False
	
	def get_list(self, amount, namespace="0"):
		query = {"action" : "query", "list" : "random", "rnnamespace" : namespace, "rnlimit" : str(amount), "prop" : "info"}
		try:
			xml = parseString(self.post(query))
		except TypeError:
			return []
		pages = []
		for page in xml.getElementsByTagName("page"):
			pages.append({"title" : page.attributes["title"].value, "id" : page.attributes["id"].value})
		return pages
	
	def get_image(self, title):
		query = {"action" : "query", "prop" : "imageinfo", "titles" : title,
			"iiprop" : "timestamp|user|url|size" }
		try:
			xml = parseString(self.post(query))
		except TypeError:
			return None
		image = xml.getElementsByTagName("ii")[0]
		return { "timestamp" : image.attributes["timestamp"].value,
			"user" : image.attributes["user"].value,
			"url" : image.attributes["url"].value,
			"descriptionurl" : image.attributes["descriptionurl"].value,
			"size" : int(image.attributes["size"].value),
			"width" : int(image.attributes["width"].value),
			"height" : int(image.attributes["height"].value) }
	
	def get_includelist(self, title, amount):
		query = {"action" : "query", "list" : "embeddedin", "eititle" : title, "rnnamespace" : "0", "eilimit" : "500", "prop" : "info", "eifilterredir" : "nonredirects"}
		xml = parseString(self.post(query))
		pages = []
		i = 0
		for page in xml.getElementsByTagName("ei"):
			if page.attributes["ns"].value=="0":
				pages.append({"title" : page.attributes["title"].value, "id" : page.attributes["pageid"].value})
				i += 1
				if i > amount:
					break
		return pages
		
	def get_content(self, title, section=None):
		query = {}
		if section!=None:
			query = {"section" : str(section)}
		c = self.index_request(title.encode("utf-8"), "raw", query)
		if c == None:
			return None
		if "Invalid file extension found in PATH_INFO or QUERY_STRING. Raw pages must be accessed through the primary script entry point." in c:
			return None
		return c
	
	def get_title_search(self, search, amount, namespace="0|4|14|100", offset=0):
		query = {'action' : 'query', 'list' : 'search', 'srsearch' : search,
				'srnamespace' : str(namespace), 'srwhat' : 'title',
				'srlimit' : str(amount), 'sroffset' : str(offset)}
		xml = parseString(self.post(query))
		pages = []
		for page in xml.getElementsByTagName('p'):
			if page.attributes['ns'].value==str(namespace):
				pages.append({"title" : page.attributes["title"].value})
		return pages
		
	def get_text_search(self, search, amount, namespace="0|4|14|100", offset=0):
		query = {'action' : 'query', 'list' : 'search', 'srsearch' : search,
				'srnamespace' : str(namespace), 'srwhat' : 'text',
				'srlimit' : str(amount), 'sroffset' : str(offset)}
		xml = parseString(self.post(query))
		pages = []
		for page in xml.getElementsByTagName('p'):
			if page.attributes['ns'].value==str(namespace):
				pages.append({"title" : page.attributes["title"].value})
		return pages
	
	def get_category_pages(self, category, amount, namespace="0|4|14|100", offset=0):
		query = {'action' : 'query', 'list' : 'categorymembers', 
				'cmtitle' : category, 'cmprop' : 'ids|title', 
				'cmnamespace' : str(namespace), 'cmlimit' : str(amount) }
		xml = parseString(self.post(query))
		pages = []
		i = 0
		namespaces = str(namespace).split('|')
		for page in xml.getElementsByTagName("cm"):
			if page.attributes["ns"].value in namespaces:
				pages.append({"title" : page.attributes["title"].value, "id" : page.attributes["pageid"].value})
				i += 1
				if i > amount:
					break
		return pages
	
	def get_recentchanges(self, amount, start=None, namespace="0|4|14|100", botedits=False):
		if start==None:
			start = ''
		query = {'action' : 'query', 'list' : 'recentchanges',
				'rclimit' : str(amount), 'rcnamespace' : str(namespace), 
				'rcprop' : 'ids|title'}
		if start!=None and start!='':
			query.update({'rcend' : start})
		if botedits:
			query.update({'rcshow' : '!redirect'})
		else:
			query.update({'rcshow' : '!bot|!redirect'})
		try:
			xml = parseString(self.post(query))
		except TypeError:
			return []
		pages = []
		i = 0
		namespaces = str(namespace).split('|')
		for page in xml.getElementsByTagName("rc"):
			if page.attributes["ns"].value in namespaces:
				pages.append({"title" : page.attributes["title"].value,
					"id" : page.attributes["pageid"].value,
					"type" : page.attributes["type"].value,
					"rcid" : page.attributes["rcid"].value,
					"revid" : page.attributes["revid"].value,
					"old_revid" : page.attributes["old_revid"].value})
				i += 1
				if i > amount:
					break
		return pages
	
	def get_user(self, user):
		query = {'action' : 'query', 'list' : 'users',
				'ususers' : user, 'usprop' : 'blockinfo|groups|editcount|registration|emailable|gender'}
		xml = parseString(self.post(query))
		tmp = None
		for user in xml.getElementsByTagName('user'):
			groups = []
			for group in user.getElementsByTagName('g'):
				groups.append(group.firstChild.data)
			tmp = {'groups' : groups,
				'editcount' : user.attributes['editcount'].value,
				'registration' : user.attributes['registration'].value,
				'emailable' : user.hasAttribute('emailable'),
				'gender' : user.attributes['gender'].value}
		return tmp
	
	def get_edit(self, revid, old_revid):
		if old_revid == None:
			revids = revid
		else:
			revids = "%s|%s" % (revid, old_revid)
		query = {'action' : 'query',
				'revids' : revids, 'prop' : 'revisions',
				'rvprop' : 'ids|flags|user|userid|size|comment|content'}
		xml = parseString(self.post(query))
		after = None
		before = None
		for page in xml.getElementsByTagName("rev"):
			try:
				c = page.firstChild.data
			except AttributeError:
				c = None
			tmp = {'user' : page.attributes["user"].value,
				'userid' : page.attributes["userid"].value,
				'revid' : page.attributes["revid"].value,
				'size' : page.attributes["size"].value,
				'comment' : page.attributes["comment"].value,
				'content' : c,
				'anon' : page.hasAttribute('anon'),
				'minor' : page.hasAttribute('minor')}
			if page.attributes['revid'].value == revid:
				after = tmp
			else:
				before = tmp
		return (before, after)
	

	
	def __init__(self, server=None, debug=False):
		if server!=None:
			self.server = server
			self.url = "http://%s/api.php" % server
			self.indexurl = "http://%s/index.php" % server
		self.debugmode = debug
