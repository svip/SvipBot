# -*- encoding: utf-8 -*-

from optparse import OptionParser
from logindata import userdata
from api import Api
from pages import Pages
from changes import Changes
from sitetasks import Tasks
from taskmanager import Taskmanager
from images import Images
import re,sys,os,time

os.chdir("/home/svip/svipbot/")

class Svipbot(object):
	api = None
	poolapi = None
	loglines = []
	debugmode = False
	writetime = True
	oldts = None
	ts = None
	newts = None
	pages = None
	images = None
	
	def check_for_lock(self):
		if os.path.exists("botlock"):
			self.log("Botlock file exists.")
			return False
		self.log("No botlock.")
		return True
		
	def log(self, msg=None, view=True):
		if msg==None:
			return self.loglines
		else:
			self.loglines.append(msg)
			if (self.debugmode or self.verbose) and view:
				print msg
	
	def log_obtain(self, obj):
		if obj==None:
			return
		for l in obj.get_log():
			self.log(l, False)
		obj.clear_log()
	
	def initiate(self):
		f = open('botlock', 'w')
		f.write('x')
		f.close()
		self.log("Wrote botlock.")
		try:
			f = open('time', 'r')
			self.ts = f.read().strip()
			self.log("Found time of `%s'." % self.ts)
			f.close()
		except IOError:
			self.ts = None # just to make sure
		# create a timestamp now, because the edits may take time, and someone could
		# make an edit in between, and we want to catch that.
		self.newts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
		
	def finish(self):
		# current time
		if self.newts==None:
			ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
		else:
			ts = self.newts
		if self.writetime:
			f = open('time', 'w')
			f.write(ts)
			f.close()
			self.log("Wrote timestamp of `%s'." % ts)
		# remove botlock
		os.remove("botlock")
		self.log("Removed botlock")
		
	def writelog(self):
		if not self.debugmode:
			# log
			fn = "logs/runlog-%s" % time.strftime("%Y%m%dT%H%M", time.gmtime())
			log = open(fn, 'w')
			log.writelines([unicode("%s\n"%s).encode('utf-8') for s in self.log()])
			log.close()
			
	def __init__(self):
		# detect args
		parser = OptionParser()
		parser.add_option("-d", "--debug", dest="debug",
				action="store_true", help="set debug mode", default=False)
		parser.add_option("-v", "--verbose", dest="verbose",
				action="store_true", help="verbose mode", default=False)
		parser.add_option("-p", "--page", dest="page",
				help="specify a page to handle")
		parser.add_option("--onepage", dest="onepage",
				action="store_true", help="only handle a single page (similar to `--pages=1')", default=False)
		parser.add_option("--task", dest="task",
				help="run builtin task (use `--task=help' for list of tasks)")
		parser.add_option("--pages", dest="pagestorun",
				help="number of pages to handle")
		parser.add_option("-s", "--search", dest="search",
				help="search string")
		parser.add_option("-t", "--time", dest="time",
				help="set time in format YYYY-MM-DDTHH:MM:SSZ")
		parser.add_option("--titlesearch", dest="titlesearch",
				action="store_true", help="search in titles rather than text", default=False)
		parser.add_option("--writetime", dest="writetime",
				action="store_true", help="write timestamp at end of run, even if other variables would disable that", default=False)
		parser.add_option("-r", "--ref", "--loadref", dest="loadref",
				action="store_true", help="force appearance reference load from wiki", default=False)
		parser.add_option("--localref", dest="localref",
				action="store_true", help="force appearance reference to be loaded locally", default=False)
		parser.add_option("--runtasks", dest="runtasks",
				action="store_true", help="force run tasks", default=False)
		parser.add_option("--changes", dest="changes",
				help="maximum recent changes to run")
		parser.add_option("--nochanges", dest="nochanges",
				action="store_true", help="don't check recent changes", default=False)
		parser.add_option("--donotfixpages", dest="donotfixpages",
				action="store_true", help="no page cleanup", default=False)
		parser.add_option("--donotrunpool", dest="donotrunpool",
				action="store_true", help="don't run changes for the pool", default=False)
		(options, args) = parser.parse_args()
		# set debug mode
		self.debugmode = options.debug
		self.verbose = options.verbose
		self.api = Api(debug=self.debugmode, server="theinfosphere.org")
		self.poolapi = Api(debug=self.debugmode, server="pool.theinfosphere.org")
		if self.debugmode:
			self.log("==== Debug mode!")
		if options.task!=None:
			# oh noes, we need to run a builtin task, so we should not run
			# regular tasks
			taskmanager = Taskmanager(debug=self.debugmode, api=self.api, verbose=self.verbose)
			if options.task == 'help':
				print taskmanager.help_response()
			else:
				self.log("Builtin task run...")
				if self.api.login(userdata.username, userdata.password):
					if not taskmanager.run_task(options.task):
						self.log("Task `%s' did not run properly or does not exist." % options.task)
				else:
					self.log("Could not log in.")
				self.writelog()
		else:
			if not options.nochanges:
				self.changes = Changes(debug=self.debugmode, api=self.api, verbose=self.verbose)
				if options.changes != None:
					self.changes.maximum = options.changes
			self.runtasks = options.runtasks
			self.pages = Pages(debug=self.debugmode, api=self.api, verbose=self.verbose)
			self.pages.singlepage = self.page = options.page
			pagestorun = 0
			if options.onepage:
				pagestorun = 1
			if options.pagestorun != None:
				pagestorun = options.pagestorun
			self.pages.pagestorun = self.pagestorun = pagestorun
			self.pages.search = self.search = options.search
			self.pages.titlesearch = self.titlesearch = options.titlesearch
			if options.time!=None:
				try:
					time.strptime(options.time, "%Y-%m-%dT%H:%M:%SZ")
					self.ts = options.time
					self.log("Using input time of `%s'." % self.ts)
				except ValueError:
					self.log("Input time given `%s' does not match format; ignoring." % self.ts)
					self.ts = None
			if self.debugmode or self.search!=None or self.pagestorun==1 or self.page!=None or self.ts!=None:
				# if any of these are the case, then writing a new time stamp could
				# mess up future runs
				self.writetime = False
			if options.writetime:
				# unless of course, it is forced by the user
				self.writetime = True
			self.pages.ar.loadref = options.loadref
			self.pages.ar.localref = options.localref
			# insure the api knows, so it won't make edits if debug mode
			if self.api.login(userdata.username, userdata.password):
				self.log("Logged in successfully.")
				if self.check_for_lock():		   
					self.initiate()
					if not options.nochanges:
						self.changes.set_ts(self.ts)
					self.pages.set_ts(self.ts)
					if self.runtasks or (self.pagestorun==0 and self.page == None):
						tasks = Tasks(self.debugmode, self.api, self.verbose, self.pages)
						self.log_obtain(tasks)
					if not options.nochanges:
						self.changes.handle_changes()
						self.log_obtain(self.changes)
					else:
						self.log("Not running recent changes checking...")
					if not options.donotfixpages:
						self.pages.routine_run()
					else:
						self.log("Not running page fixing...")
					self.log_obtain(self.pages)
					if not options.donotrunpool:
						self.images = Images(debug=self.debugmode, api=self.api, verbose=self.verbose, poolapi=self.poolapi)
						self.images.routine_job(self.ts)
						self.log_obtain(self.images)
					else:
						self.log("Not running through the pool...")
					self.finish()
			else:
				self.log("Could not log in.")
			self.writelog()
