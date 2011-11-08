# -*- encoding: utf-8 -*-

from basic import Basic
from api import Api
from quotes import Quotes
import quotes
from appearref import AppearRef
from categories import Categories
import re
from urllib import unquote

class Pages(Basic):
	"""The general class for handling pages and modifications to be done to
	these pages.  Yes, a lot of these are Infosphere specific."""

	ts = None
	pages = []
	search = None
	titlesearch = False
	onepage = False
	pagestorun = 0
	singlepage = None
	ar = None
	
	def appearance_list_fix(self, content):
		r = re.compile(r"={3} ?(Appearances?|Mentions?) ?={3}", re.I)
		if not r.search(content):
			return content
		section = ''
		inappear = False
		incomment = False
		for line in content.splitlines():
			if re.search("<!--", line):
				incomment = True
			if re.search("-->", line):
				incomment = False
			if inappear:
				if re.match("={2,3}", line, re.I) and not incomment:
					section = "%s\n" % section
					inappear = False
				elif re.match("\*", line):
					section = "%s%s\n" % (section, line)
			if re.match("={2,3}.*(Appearances?|Mentions?).*={2,3}", line, re.I) and not incomment:
				inappear = True
		work = "%s" % section
		if re.search(r"\{\{appear-begin\}\}", content):
			return content
		t = []
		[t.append(a) for a in re.split(r"\n?\*", work) if a.strip()!='']
		if len(t)>15:
			work = "{{appear-begin}}\n%s\n{{appear-end}}\n" % work.strip()
		return content.replace(section, work)
	
	def category_arrangement(self, content, title, overwrite_categories=None, infobox_categories=None):
		c = self.categories.page(content, title)
		self.log_obtain(self.categories)
		return c
	
	def unquote(self, s):
		result = s
		try:
			if '%u' in result:
				result = result.replace('%u','\\u').decode('unicode_escape')
			result = unquote(result)
			result = result.encode("latin1").decode("utf8")
		except UnicodeEncodeError:
			pass
		except UnicodeDecodeError:
			result = s
		return result
	
	def firstlower(self, s):
		try:
			return s[0].lower() + s[1:]
		except IndexError:
			return s.lower()
	
	def general_link_cleaning(self, mo):
		linkcontent = mo.group(1)
		viewcontent = None
		if "|" in linkcontent:
			t = linkcontent.split("|", 1)
			viewcontent = t[1]
			linkcontent = t[0]
		# remove underscores from links and replace them with a space
		linkcontent = linkcontent.replace("_", " ")
		bookcontent = None
		if "#" in linkcontent:
			t = linkcontent.split("#", 1)
			bookcontent = t[1]
			linkcontent = t[0]
			r = re.compile("\.([1-9abcdef][0-9abcdef])", re.I)
			bookcontent = r.sub(r"%\1", bookcontent)
			bookcontent = self.unquote(bookcontent)
		elif viewcontent != None:
			if self.firstlower(linkcontent) == self.firstlower(viewcontent):
				# if they are the same, then just use viewcontent.
				linkcontent = viewcontent
				viewcontent = None
		if bookcontent != None:
			linkcontent = "%s#%s" % (linkcontent, bookcontent)
		if ":" in linkcontent:
			t = linkcontent.split(":", 1)
			interwikisite = t[0]
			interwikipage = t[1]
			if interwikisite == 'wikipedia':
				if self.firstlower(interwikipage) == self.firstlower(viewcontent):
					# if they are the same, then just use viewcontent.
					interwikipage = viewcontent
					viewcontent = None 
				if viewcontent == None:
					return "{{w|%s}}" % interwikipage
				else:
					return "{{w|%s|%s}}" % (interwikipage, viewcontent)
		if viewcontent == None:
			return "[[%s]]" % linkcontent
		else:
			return "[[%s|%s]]" % (linkcontent, viewcontent)

	def general_cleanup(self, content, title):
		work = content
		# tidy up headline articles.
		self.log("		* Tidying headline")
		r = re.compile(r"^(=+)(.*?)(=+)$", re.MULTILINE)
		work = r.sub(self.headline_spacing, work)
		# add a line before each headlines
		self.log("		* Spacing headlines")
		r = re.compile(r"([^\n]*)\n(=+)(.*?)(=+)\n")
		work = r.sub(self.headline_tidying, work)
		# trim triple line feeds
		self.log("		* Removing triple+ lines")
		r = re.compile(r"\n[ \t]*\n[ \t]*\n")
		work = r.sub("\n\n", work)
		# date clean up
		self.log("		* Fixing dates")
		r = re.compile(r"([a-zA-Z]*) ([1-9][0-9]?)(st|th|rd|nd|)([\.,\?!]?[^0-9])", re.I)
		work = r.sub(self.date_cleanup, work)
		# image to file
		self.log("		* Image: to File:")
		r = re.compile(r"\[\[image:", re.I)
		work = r.sub("[[File:", work)
		# general link cleaning
		self.log("		* General link fixing")
		r = re.compile("\[\[(.*?)\]\]")
		work = r.sub(self.general_link_cleaning, work)
		# appearance list
		self.log("		* Appearance list")
		work = self.appearance_list_fix(work)
		return work
	
	def contains_bot_comment(self, content):
		if content.count("<!-- Bot comment") > 0:
			return True
		return False
	
	def fix_quotes(self, content, title):
		# first detect if this article has a detect section.
		if not quotes.has_quote_section(content):
			return content
		# let's get that section out
		section = quotes.get_quote_section(content)
		if section == None:
			return content
		# throw it off to our parser.
		q = Quotes(section)
		tmp = q.get_content()
		if self.debugmode:
			print q.get_content()
		final = content.replace(section, tmp)
		self.log_obtain(q)
		if final==None: # in case we got nothing.
			return content
		return final
	
	def headline_spacing(self, mo):
		return "%s %s %s" % (mo.group(1), mo.group(2).strip(), mo.group(3))
	
	def headline_tidying(self, mo):
		t = ''
		if mo.group(1).strip()!='':
			t += mo.group(1)+'\n'
		else:
			t += '\n'
		t += "\n%s %s %s\n" % (mo.group(2), mo.group(3).strip(), mo.group(4))
		return t
	
	def date_cleanup(self, mo):
		months = ['January', 'February', 'March', 'April', 'May',
				'June', 'July', 'August', 'September', 'October',
				'November', 'December']
		month = mo.group(1)
		if not month.capitalize() in months:
			return mo.group(0)
		return "%s %s%s" % (mo.group(2), mo.group(1), mo.group(4))

	def get_routine_pages(self):
		if self.ts != None:
			self.pages = self.api.get_recentchanges(500, self.ts, "0|4|14")
			if len(self.pages) == 0:
				if self.pagestorun>0:
					self.pages = self.api.get_list(self.pagestorun)
					self.log("No changes in recent changes since %s, so using %s random pages instead." % (self.ts, self.pagestorun))
				else:
					self.pages = self.api.get_list(5)
					self.log("No changes in recent changes since %s, so using 5 random pages instead." % self.ts)
			else:
				self.log("Found %s changes since %s." % (len(self.pages), self.ts))
		else:
			if self.pagestorun>0:
				self.log("No escape time defined, just checking the previous %s recent changes, then." % self.pagestorun)
				self.pages = self.api.get_recentchanges(self.pagestorun)
			else:
				self.log("No escape time defined, just checking the previous ten recent changes, then.")
				self.pages = self.api.get_recentchanges(10)
	
	def get_pages(self):
		if self.search == None:
			if self.singlepage != None:
				self.pages = [{'title' : self.singlepage}]
				self.log("Only handling `%s'..." % self.singlepage)
			else:
				self.get_routine_pages()
		else:
			if self.pagestorun != 0:
				pagestorun = self.pagestorun
			else:
				pagestorun = 10
			if self.titlesearch:
				self.log("Using %s pages for the title search term `%s'" % (pagestorun, self.search))
				self.pages = self.api.get_title_search(self.search, pagestorun)
			else:
				self.log("Using %s pages for the search term `%s'" % (pagestorun, self.search))
				self.pages = self.api.get_text_search(self.search, pagestorun)
	
	def includeonly_sub(self, mo):
		i = len(self.includeonlies)+1
		s = "__INCLUDEONLY_%s__" % i
		self.includeonlies.update({s : mo.group(0)})
		return s
	
	def noinclude_sub(self, mo):
		i = len(self.noincludes)+1
		s = "__NOINCLUDE_%s__" % i
		self.noincludes.update({s : mo.group(0)})
		return s
	
	def includes_remove(self, work, title):
		self.includeonlies = {}
		self.noincludes = {}
		work = re.sub(r"<includeonly>.*?</includeonly>", self.includeonly_sub, work, re.DOTALL | re.M)
		work = re.sub(r"<noinclude>.*?</noinclude>", self.noinclude_sub, work, re.DOTALL | re.M)
		return work
	
	def includes_insert(self, work, title):
		if len(self.includeonlies) == 0 and len(self.noincludes) == 0:
			return work
		for i in self.includeonlies:
			work = work.replace(i, self.includeonlies[i])
		for i in self.noincludes:
			work = work.replace(i, self.noincludes[i])
		return work
	
	def routine_job(self):
		donepages = []
		for page in self.pages:
			if page['title'] in donepages:
				continue
			donepages.append(page['title'])
			title = page['title']
			self.log("Handling page `%s'..." % title)
			work = content = self.api.get_content(title)
			if work==None:
				self.log("	> No content found, assuming deleted.")
				continue
			if self.contains_bot_comment(work):
				self.log("	> Bot comment found in content, avoid changing content.")
				continue
			# striping includeonly
			self.includeonlies = {}
			self.log("	* Removing includeonly's...")
			work = self.includes_remove(work, title)
			# quotes
			self.log("	* Fixing its quotes...")
			work = self.fix_quotes(work, title)
			# arrange categories
			self.log("	* Arranging its categories...")
			work = self.category_arrangement(work, title)
			# fix links
			self.log("	* Fixing its reference links...")
			work = self.ar.ref_links(work, title)
			self.log_obtain(self.ar)
			# ...
			
			# general cleanup
			self.log("	* General cleanup...")
			work = self.general_cleanup(work, title)
			# reapply includeonlies
			self.log("	* Reinserting includeonly's...")
			work = self.includes_insert(work, title)
			# finish off
			if work != content:
				self.log("	> Changes made, commiting edit...")
				if not self.api.edit_page(title, work, "Bot edit: General fixes, etc."):
					self.log("	>> Edit failed.")
			else:
				self.log("	> No changes made, ommitting an edit")
			if len(donepages) >= self.pagestorun and self.pagestorun != 0:
				break
	
	def routine_run(self):	
		if len(self.pages) == 0:
			self.get_pages()
		self.routine_job()
		self.pages = []

	def set_ts(self, ts):
		self.ts = ts
		self.ar.ts = self.ts
		self.ar.obtain_appear_data()
		self.log_obtain(self.ar)
	
	def __init__(self, debug, api, verbose):
		Basic.__init__(self, debug, api, verbose)
		self.ar = AppearRef(debug=self.debugmode, api=self.api, verbose=self.verbose)
		self.categories = Categories(debug=self.debugmode, api=self.api, verbose=self.verbose)
