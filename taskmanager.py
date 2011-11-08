# -*- encoding: utf-8 -*-

from basic import Basic
from tasks import *

class Taskmanager(Basic):
	"""These are special case tasks that can only be done by running the bot from
	a terminal; these will *never* be part of a cronjob run (unless if you specify
	it to do so), as these are designed for big tasks that are necessary, but
	seldomly required.
	
	These tasks can be easily be seen by running ./botcronjob.py --task=help
	
	Currently this includes updating all appearance-related information on the
	Infosphere; such as when new episode titles become known, these will be there
	to update it across the wiki (wherever the appropriate appearance tags are
	used)."""

	tasks = {'eref' : ['Update the e-reference templates', eref.Eref]}

	def help_response(self):
		r = """Known tasks (--task=TASK):
"""
		for t in self.tasks:
			r += "\n%s:  %s" % (t, self.tasks[t][0])
		return r

	def run_task(self, task):
		try:
			test = self.tasks[task]
		except (KeyError):
			return False
		c = test[1](debug=self.debugmode, api=self.api, verbose=self.verbose)
		r = c.run()
		self.log_obtain(c)
		return r

	def __init__(self, debug, api, verbose):
		Basic.__init__(self, debug, api, verbose)
		self.debugmode = debug
		self.api = api
