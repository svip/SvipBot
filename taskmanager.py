# -*- encoding: utf-8 -*-

from basic import Basic
from tasks import *

class Taskmanager(Basic):

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
