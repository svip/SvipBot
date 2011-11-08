# -*- encoding: utf-8 -*-

import re
from basic import Basic
import time
import pickle, os

class AppearRef(Basic):
	"""This file contains *specific* Infosphere-related mechanics.
	It deals with episodes, comics, etc.; all that appears in the appearance
	lists which appears in numerous articles across the Infosphere.
	
	If you are using this bot for something *else*, you will probably not
	need this code."""

	episodes = {}
	comics = {}
	typos = {}
	ts = ''
	oldts = ''
	localref = False
	loadref = False
	
	def is_something(self, what, link, type=None, searchin=['title'], typotype='e'):
		try:
			t = what[link.lower()]
		except KeyError:
			# hm, let's try typos
			try:
				t = self.typos[link.lower()]
				if t['type']!=typotype:
					return False
				t = what[t['code']]
				return True
			except KeyError:
				return False
		if type != None and t['type']!=type:
			return False
		for s in searchin:
			if t[s].lower()==link.lower():
				return True		
		return False
	
	def is_episode(self, link, searchin=['title']):
		return self.is_something(self.episodes, link, 'e', searchin, 'e')
	
	def is_film(self, link, searchin=['title']):
		return self.is_something(self.episodes, link, 'f', searchin, 'f')
	
	def is_comic(self, link, searchin=['title']):
		return self.is_something(self.comics, link, None, searchin, 'c')
	
	def get_title(self, what, link, typotype):
		try:
			t = what[link.lower()]
		except KeyError:
			try:
				t = self.typos[link.lower()]
				if t['type']!=typotype:
					return None
				t = what[t['code']]
			except KeyError:
				return None
		return t['title']
	
	def get_episode_title(self, link):
		return self.get_title(self.episodes, link, 'e')
	
	def get_film_title(self, link):
		return self.get_title(self.episodes, link, 'f')
	
	def get_comic_title(self, link):
		return self.get_title(self.comics, link, 'c')
	
	def handle_links(self, mo):
		left = mo.group(1)#.rstrip()
		right = mo.group(3)#.lstrip()
		link = mo.group(2).strip()
		if self.is_episode(link, ['title']):
			if len(left) > 0 and left[-1]!='"':
				left = '%s"' % left
			if len(right) > 0 and right[0]!='"':
				if right[0] in [',','.']:
					if right[1] == '"':
						right = '"%s' % right[0]
					else:
						right = '"%s' % right
				else:
					right = '"%s' % right
			# sanity checks
			if right[0:2]=='"\'' and left[-2:2]=='\'"':
				right = right.replace("'", '')
				left = left.replace("'", '')
			title = self.get_episode_title(link)
			return '%s[[%s]]%s' % (left, title, right)
		if self.is_film(link, ['title']):
			leftapp = ''
			rightapp = ''
			if left!="''":
				leftapp="''"
			if right!="''":
				rightapp="''"
			title = self.get_film_title(link)
			return '%s%s[[%s]]%s%s' % (left, leftapp, title, rightapp, right)
		if self.is_comic(link, ['title']):
			if len(left) > 0 and left[-1]!='"':
				left = '%s"' % left
			if len(right) > 0 and right[0]!='"':
				if right[0] in [',','.']:
					if right[1] == '"':
						right = '"%s' % right[0]
					else:
						right = '"%s' % right
				else:
					right = '"%s' % right
			title = self.get_comic_title(link)
			return '%s[[%s]]%s' % (left, title, right)
		return '%s' % mo.group(0)
	
	def get_episode(self, title):
		try:
			t = self.episodes[title.lower()]
		except KeyError:
			try:
				t = self.typos[title.lower()]
			except KeyError:
				return None
		return t
	
	def handle_templatelinks(self, mo):
		if mo.group(2)=='|':
			if mo.group(1)=='f':
				# film!
				title = mo.group(3).strip()
				t = self.get_episode(title)
				if t==None:
					return mo.group(0)
				return "{{f|%s}}" % t['no']
			elif mo.group(1)=='e':
				# episode!
				title = mo.group(4).strip()
				t = self.get_episode(title)
				if t==None:
					return mo.group(0)
				return "{{e|%s}}" % t['code']
			elif mo.group(1)=='eni':
				# episode with no icon
				title = mo.group(3).strip()
				t = self.get_episode(title)
				if t==None:
					return mo.group(0)
				return '"[[%s]]"' % t['title']
		else:
			if mo.group(1)=='f':
				# film!
				title = mo.group(3).strip()
				t = self.get_episode(title)
				if t==None:
					return mo.group(0)
				return "''[[%s]]''" % t['title']
			elif mo.group(1)=='e':
				# episode!
				title = mo.group(4).strip()
				t = self.get_episode(title)
				if t==None:
					return mo.group(0)
				return '"[[%s]]"' % t['title']
		return mo.group(0)
		
	def ref_links(self, content, title):
		work = content
		r = re.compile("(.{2})\[\[([^\|\]]*)\]\](.{2})", re.MULTILINE | re.DOTALL)
		work = r.sub(self.handle_links, work)
		r = re.compile("\{\{(e|f)link(\/noicon\||\|)([^\|\}]+)\|?([^\|\}]*)\}\}")
		work = r.sub(self.handle_templatelinks, work)
		r = re.compile("\{\{(eni)(\|)([^\}]*)\}\}")
		work = r.sub(self.handle_templatelinks, work)
		return work
	
	def handle_appear_data(self, page):
		refs = {}
		syntax = []
		content = self.api.get_content(page)
		for line in content.splitlines():
			if line[0]=='#':
				continue
			if len(syntax)==0:
				# assume this is the syntax
				t = line.split("|")
				for a in t:
					if ":" in a:
						a = a.split(":")
						syntax.append((a[0], True))
					else:
						syntax.append((a, False))
			else:
				erefUse = True
				if line[-1]==':':
					erefUse = False
					line = line[:-1]
				t = line.split("|")
				i = 0
				tmp = {'eref' : erefUse}
				lookup = []
				for e in t:
					if syntax[i][1]:
						lookup.append(e)
						if e!=e.lower():
							lookup.append(e.lower())
					tmp.update({syntax[i][0] : e})
					i+=1
				for l in lookup:
					refs.update({l : tmp})
		return refs
	
	def isnewday(self, ts):
		if ts==None:
			return False
		try:
			t = time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
		except ValueError:
			return False
		try:
			n = time.strptime(self.ts, "%Y-%m-%dT%H:%M:%SZ")
		except ValueError:
			return False
		return t.tm_yday!=n.tm_yday
	
	def pickles_exist(self):
		if not os.path.exists("appearref-comics"):
			return False
		if not os.path.exists("appearref-episodes"):
			return False
		if not os.path.exists("appearref-typos"):
			return False
		return True
	
	def obtain_appear_data(self, doit=False):
		if self.episodes != {} and self.comics != {} and self.typos != {}:
			# no need to do it this if it has already been done.
			return
		# only obtain the appearref from the wiki at least once
		# a day.  Of course, you can overwrite this with --loadref
		if doit or (not self.localref and (self.loadref or self.oldts==None 
			or self.isnewday(self.oldts) or not self.pickles_exist())):
			comicpage = "MediaWiki:AppearRef/comics"
			episodepage = "MediaWiki:AppearRef/episodes"
			typopage = "MediaWiki:AppearRef/commontypos"
			self.comics = self.handle_appear_data(comicpage)
			self.episodes = self.handle_appear_data(episodepage)
			self.typos = self.handle_appear_data(typopage)
			self.log("Appearance reference data obtained from wiki.")
			f = open("appearref-comics", 'w')
			pickle.dump(self.comics, f)
			f.close()
			f = open("appearref-episodes", 'w')
			pickle.dump(self.episodes, f)
			f.close()
			f = open("appearref-typos", 'w')
			pickle.dump(self.typos, f)
			f.close()
			self.log("Wrote appearance reference data to pickle.")
		else:
			# let's just load the content from pickle, should be snappy.
			f = open("appearref-comics")
			self.comics = pickle.load(f)
			f.close()
			f = open("appearref-episodes")
			self.episodes = pickle.load(f)
			f.close()
			f = open("appearref-typos")
			self.typos = pickle.load(f)
			f.close()
			self.log("Appearance reference data obtained from pickle.")
	
	def __init__(self, debug, api, verbose):
		Basic.__init__(self, debug, api, verbose)
		self.debugmode = debug
		self.api = api
