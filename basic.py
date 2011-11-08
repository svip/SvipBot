# -*- encoding: utf-8 -*-

class Basic(object):
	"""This is the basic object for all the parts of the systems of the bot.
	It allows each class to easily log its output; whether verbose or not and
	to save it in a log file."""

	loglines = []
	debugmode = False
	verbose = False
	api = None
	
	"""Obtain the current log a class has written, so that it can be combined
	with the full log."""
	def log_obtain(self, obj):
		if obj==None:
			return
		for l in obj.get_log():
			self.log(l, False)
		obj.clear_log()
	
	"""Log message."""
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
	
	"""Get the log."""	
	def get_log(self):
		return self.loglines
	
	"""Clears its log."""
	def clear_log(self):
		self.loglines = []
	
	"""Init the class."""
	def __init__(self, debugmode, api, verbose):
		self.loglines = []
		self.debugmode = debugmode
		self.api = api
		self.verbose = verbose
