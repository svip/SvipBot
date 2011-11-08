# -*- encoding: utf-8 -*-

from basic import Basic
from pages import Pages
import pickle

class Tasks(Basic):
	"""These are tasks to be run by the bot; they are more specific than the more
	general page handling task, etc.  These include (for now at least); check
	the pages of an entire category and move a category."""
	
	def run_category(self, category, doall=False):
		if doall:
			self.pages.pages = self.api.get_category_pages('Category:%s' % category, 500, '0|1|2|3|4|5|6|7|8|9|10|11|12|13|14|100|101|102|103|104|105|106|107|108')
		else:
			self.pages.pages = self.api.get_category_pages('Category:%s' % category, 500)
		self.pages.routine_run()
		self.log_obtain(self.pages)
	
	def category_focus_task(self):
		content = self.api.get_content('User:SvipBot/tasks/categories')
		if content == None:
			return False
		for line in content.splitlines():
			if line[0] == '#':
				continue
			break
		if line=='' or line==None or line[0] == '#':
			self.log('Tasks: No category found to task.')
			return False
		category = line
		self.log('Tasks: Found category `%s\' to run through.' % category)
		self.run_category(category)
		content = content.replace('\n%s' % category, '')
		self.api.edit_page('User:SvipBot/tasks/categories', content, 'Bot edit: Done with focus for task category `%s\'.' % category)
		return True
	
	def category_move_task(self):
		content = self.api.get_content('User:SvipBot/tasks/categorymove')
		if content == None:
			return False
		for line in content.splitlines():
			if line[0] == '#':
				continue
			break
		if line == '' or line == None or line[0] == '#':
			self.log('Tasks: No category move task found.')
			return False
		try:
			t = line.split('|')
			oldcategory = t[0]
			newcategory = t[1]
		except AttributeError, IndexError:
			self.log('Tasks: Something wrong with the category move syntax, I better not do anything.')
			return False
		if oldcategory == '' or newcategory == '':
			self.log('Tasks: Something wrong with the category move syntax, run!')
			return False
		self.log('Tasks: Moving category `%s\' to `%s\'.' % (oldcategory, newcategory))
		# first, let's check if new category already has a page.
		if self.api.get_content('Category:%s' % newcategory) == None:
			# okay, it doesn't, let's make it then
			oldcontent = self.api.get_content('Category:%s' % oldcategory)
			if oldcontent == None:
				# wait, what?
				self.log('Tasks: Old category did not exist.  I\'m going for coffee.')
				return False
			# good, now let's shove that into the new category page.
			self.api.create_page('Category:%s' % newcategory, oldcontent, 'Bot creating category for movage.')
		# then let's ensure the old category is a redirect (even if the new category
		# already exists, the user may not have done ALL the work)
		if not self.api.edit_page('Category:%s' % oldcategory, '#REDIRECT [[:Category:%s]]' % newcategory, 'Bot creating redirect to new category.'):
			self.log('Tasks: Could not create redirect.  Bail!')
			return False
		self.pages.categories.add_replace_cats(oldcategory, newcategory)
		self.run_category(oldcategory, True)
		content = content.replace('\n%s|%s' % (oldcategory, newcategory), '')
		self.api.edit_page('User:SvipBot/tasks/categorymove', content, 'Bot removing recently run category move.')
		return True
	
	def run_basic_tasks(self):
		self.category_focus_task()
		self.category_move_task()
	
	def __init__(self, debug, api, verbose, pages):
		Basic.__init__(self, debug, api, verbose)
		self.pages = pages
		self.run_basic_tasks()
