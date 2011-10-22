# -*- encoding: utf-8 -*-

class Basic(object):

	loglines = []
	debugmode = False
	verbose = False
	api = None
	
	def log_obtain(self, obj):
		if obj==None:
			return
		for l in obj.get_log():
			self.log(l, False)
		obj.clear_log()
	
	def log(self, msg, view=True):
		if (self.debugmode or self.verbose) and view:
			try:
				print msg
			except UnicodeEncodeError:
				try:
					print msg.encode('latin-1')
				except UnicodeEncodeError:
					print "I can't print this message."
		self.loglines.append(msg)
	
	def get_log(self):
		return self.loglines
	
	def clear_log(self):
		self.loglines = []
	
	def __init__(self, debugmode, api, verbose):
		self.loglines = []
		self.debugmode = debugmode
		self.api = api
		self.verbose = verbose
