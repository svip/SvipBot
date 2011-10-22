# -*- encoding: utf-8 -*-

import re
from basic import Basic
import pickle, random, os

class Categories(Basic):
	tmp = {}
	content = ''
	badcats = ['Primary Characters', 
			'Secondary Characters', 'Tertiary Characters',
			'Deceased Characters', 'Celebrity Guests',
			'Special guests',
			'Season 1 Episodes', 'Season 2 Episodes',
			'Season 3 Episodes', 'Season 4 Episodes',
			'Season 5 Episodes', 'Season 6 Episodes']
	replacecats = []
	infoboxcats = {
		r'\{\{[Ee]pisode infobox' : ['Episodes', 'Media'],
		r'\{\{[Cc]omic infobox' : ['Comics', 'Media'],
		r'\{\{[Cc]haracters infobox' : ['Characters'],
		r'\{\{[Cc]ommentary infobox' : ['Commentaries', 'DVD box sets']
	}
	
	def get_badcats(self):
		if random.randint(0, 10) < 2 or not os.path.exists('badcats'):
			c = self.api.get_content('User:SvipBot/data/badcats')
			if c == None:
				self.badcats = []
				return False
			tmp = []
			for line in c.splitlines():
				if line[0] == '#':
					continue
				if line != '' and line != None:
					tmp.append(line)
			self.badcats = tmp
			f = open('badcats', 'w')
			pickle.dump(self.badcats, f)
			f.close()
		else:
			f = open("badcats")
			self.badcats = pickle.load(f)
			f.close()
	
	def add_replace_cats(self, old, new):
		self.replacecats.append((old, new))

	def addcat(self, mo):
		cat = mo.group(1)
		if '|' in cat:
			cat = cat.split('|')
			c = cat[0].strip()
			c = c[0].upper() + c[1:]
			self.tmp.update({c : [cat[1], None]})
		else:
			c = cat.strip()
			c = c[0].upper() + c[1:]
			self.tmp.update({c : [None, None]})
		return ''
	
	def catsort(self, x, y):
		x = x[0]
		y = y[0]
		i = 0
		while ord(x[i])==ord(y[i]):
			i+=1
			try:
				t = x[i]
			except (KeyError, IndexError):
				return -1
			try:
				t = y[i]
			except (KeyError, IndexError):
				return 1
		return ord(x[i])-ord(y[i])

	def category_arrangement(self, content, title, overwrite_categories=None, infobox_categories=None):
		self.tmp = {}
		r = re.compile( r"\[\[Category\:(.*?)\]\]", re.I )
		r.sub(self.addcat, content)
		ds = re.compile( r"\{\{DEFAULTSORT:([^\}]+)\}\}\n?" )
		try:
			defaultsort = ds.search(content).group(1)
		except AttributeError:
			defaultsort = None
		categories = self.tmp
		if overwrite_categories != None:
			for cat in overwrite_categories:
				try:
					categories[cat[0]][1] = cat[1]
				except (KeyError, IndexError):
					pass
		if infobox_categories != None:
			for cat in infobox_categories:
				try:
					categories.pop(cat)
				except (KeyError, IndexError):
					pass
		else:
			for cat in self.badcats:
				try:
					categories.pop(cat)
				except (KeyError, IndexError):
					pass
		ordercats = []
		sorts = []
		for cat in categories:
			s = None
			if defaultsort!=categories[cat][0]:
				s = categories[cat][0]
			if categories[cat][1] != None:
				# check if the category should be overwritten
				ordercats.append([categories[cat][1], s])
			else:
				ordercats.append([cat, s])
				if categories[cat][0]!=None:
					# check if it has a sort
					sorts.append(categories[cat][0])
		ordercats.sort(self.catsort)
		if defaultsort==None and len(sorts)==len(ordercats) and len(ordercats)>1:
			nodubsort = []
			[nodubsort.append(i) for i in sorts if not nodubsort.count(i)]
			if len(nodubsort)==1:
				defaultsort = nodubsort[0]
				for o in ordercats:
					if o[1] == defaultsort:
						o[1] = None
		catbox = ''
		if defaultsort!=None:
			catbox += '{{DEFAULTSORT:%s}}' % defaultsort
		for cat in ordercats:
			s = cat[0]
			if cat[1]!=None and cat[1]!=title:
				s = '%s|%s' % (cat[0], cat[1])
			catbox += '\n[[Category:%s]]' % s
		work = r.sub('', content).strip('\n ')
		work = ds.sub('', work).strip('\n ')
		final = '%s\n%s' % (work, catbox)
		self.content = final.strip('\n ')
	
	"""
	def category_replacement(self, cats, infocats, lookcats=[]):
		i = 1
		m = 50
		if len(lookcats)==0:
			for c in cats:
				lookcats.append(c[0])
		#for c in infocats:
		#	lookcats.append(c)
		for c in lookcats:
			print "Doing pages in `%s'..." % c
			pages = self.api.get_category_pages('Category:' + c, 500, '0|14')
			for p in pages:
				print "Rearranging `%s'..." % p['title'],
				if self.category_arrangement(p['title'], cats, infocats):
					print " done"
					i += 1
					if i > m:
						break
				else:
					print " skipped"
			if i > m:
				break 
			print "Next category..."
	
	def category_styles(self):
		self.category_replacement([('Heads in Jars', 'Heads in jars'), 
			('Human', 'Humans'),
			('U.S. Presidents', 'U.S. presidents'),
			('Earth President', 'Earth presidents'),
			('Farnsworth\'s Creations', 'Farnsworth\'s creations'),
			('Voice Actors', 'Voice actors'),
			('Food and Drinks', 'Food and drinks'),
			('Alien Species', 'Alien species')
		], #,
		   ['Episodes'])"""
	
	def page(self, content, title):
		self.tmp = {}
		self.content = ''
		infocats = []
		for infcat in self.infoboxcats:
			if re.search(infcat, content):
				for i in self.infoboxcats[infcat]:
					infocats.append(i)
		self.category_arrangement(content, title, self.replacecats, infocats)
		return self.content		

	def __init__(self, debug, api, verbose):
		Basic.__init__(self, debug, api, verbose)
		self.get_badcats()
