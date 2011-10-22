# -*- encoding: utf-8 -*-

from tasks.basictask import BasicTask
from appearref import AppearRef
import pickle

class Eref(BasicTask):

	ar = None
	
	def deleteTemplates(self, temps):
		for t in temps:
			self.log("Deleting `%s'..." % t)
			self.api.delete_page(t, "Deleting E-reference template for clean up...")
	
	def episode_run(self, ep):
		titletemplates = [
			"Template:E/titles/%s" % ep['no'],
			"Template:E/titles/%s" % ep['code'] ,
			"Template:E/titles/%s" % ep['title']
		]
		codetemplate = "Template:E/codes/%s" % ep['title']
		
		self.log("Writing e-reference templates for `%s'..." % ep['title'])
		# test if this is a rename!
		c = self.api.get_content(titletemplates[1])
		if c != None and c.strip() != '':
			# could be...
			deleteAll = False
			title = None
			try:
				title = c.split('</noinclude>')[1]
			except:
				# oh dear, something is wrong, better delete them all
				self.log("Something's wrong with these templates, I am going to delete them and then recreate them...")
				deleteAll = True
				alsoDelete = []
			if title != None and title != ep['title']:
				# it IS a rename!
				self.log("This is a rename!  Deleting former templates...")
				deleteAll = True
				alsoDelete = [
					"Template:E/titles/%s" % title,
					"Template:E/codes/%s" % title
				]
			if deleteAll:
				self.deleteTemplates(titletemplates + [codetemplate] + alsoDelete)
				self.log("Deletion complete; continuing...")
		titlecontent = "<noinclude>[[Category:E-reference|%s]]</noinclude>%s" % (ep['code'], ep['title'])
		codecontent = "<noinclude>[[Category:E-reference|%s]]</noinclude>%s" % (ep['code'], ep['code'])
		oneDid = False
		for t in titletemplates:
			if self.api.create_page(t, titlecontent, "Bot creating e-reference page for `%s'..." % ep['title']):
				oneDid = True
		if self.api.create_page(codetemplate, codecontent, "Bot creating e-reference page for `%s'..." % ep['title']):
			oneDid = True
		if not oneDid:
			self.log("E-references for episode `%s' already existed..." % ep['title'])
			return True
		else:
			self.log("E-references written.")
			return True
	
	def epsort(self, x, y):
		return int(x['no']) - int(y['no'])

	def run(self):
		ar = AppearRef(debug=self.debugmode, api=self.api, verbose=self.verbose)
		ar.obtain_appear_data(True)
		codesdone = []
		self.log("Reading pickle...")
		try:
			f = open("tasks/eref-codesdone", 'r')
			codesdone = pickle.load(f)
			f.close()
			self.log("Pickle read.")
		except:
			self.log("Pickle did not exist.")
		epsorted = []
		for epref in ar.episodes:
			ep = ar.episodes[epref]
			if ep['type']!='e':
				continue
			if ep['code'] in codesdone:
				continue
			if not ep['eref']:
				continue
			epsorted.append(ep)
			codesdone.append(ep['code'])
		epsorted.sort(self.epsort)
		codescertainlydone = []
		for ep in epsorted:
			if self.episode_run(ep):
				codescertainlydone.append(ep['code'])
		self.log("Checking obsolete template...")
		temppages = self.api.get_category_pages("Category:E-reference (temporary)", 50, 10)
		codestoberedone = []
		for page in temppages:
			code = page['title'].split('/')[2]
			if code in codesdone:
				self.log("Deleting `%s' as it is obsolete..." % page['title'])
				self.api.delete_page(page['title'], "Bot deleting obsolete e-reference template.")
				if not code in codestoberedone:
					codestoberedone.append(code)
		self.log("Rerunning any references with obsolete template...")
		for code in codestoberedone:
			ep = ar.episodes[code]
			self.log("Rerunning `%s'..." % ep['title'])
			self.episode_run(ep)
		self.log("Writing picking...")
		f = open("tasks/eref-codesdone", 'w')
		pickle.dump(codescertainlydone, f)
		f.close()
		self.log("All done.")
		return True

	def __init__(self, debug, api, verbose):
		BasicTask.__init__(self, debug, api, verbose)
		self.debugmode = debug
		self.api = api
