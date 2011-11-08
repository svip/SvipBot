# -*- encoding: utf-8 -*-
import re
from lxml import etree
from basic import Basic

class Quotes(Basic):
	"""Quotes are a big part of the Infosphere, and appears almost on every page,
	as such, they have a universal standard that the bot tries to fix."""

	content = ''
	top = ''
	bottom = ''
	dialogues = []
	columns = 1
	
	# static
	TALK = 0
	ACTION = 1
	TALKDESCRIBER = 2
	LINEFEED = 3
	
	def is_talk_describer(self, s):
		# the idea of this function is to figure out whether an 'action' is
		# actually describer of how the following text is.
		# This is particularly difficult as this will require some insight
		# in understanding human language.
		# So to begin with, we start with something simple; if it is just
		# a single word; there is a good chance it describes the text.
		r = re.compile(r"\w+$")
		if r.match(s.strip()):
			# it's only one word!  Good.
			return True
		# if it starts with a capital character, it's usually not a good
		# sign.  Text describers are often written in complete lowercase.
		if re.match(r"[A-Z]", s.strip()):
			return False
		# if there are pronouns in it, it is probably not a describer
		if re.search(r"(he|she|it|they|him)", s.strip(), re.I):
			return False
		# but if it contains a semi colon, it is also a good chance of it being
		# a text describer; but no comma!
		if ";" in s and not "," in s:
			return True
		# but if it is has a full stop, not a good sign either!
		if "." in s:
			return False
		# and if it ends in certain conditional writing, like '-ing' or '-ly',
		# it could be a describer as well.
		# but only with a few words, of course.
		if re.search(r"(\w+){0,2} \w+(ly|ing)$", s.strip(), re.I):
			return True
		# if it is more than 3 words, it is probably not.
		if re.match(r"\w+ \w+ \w+ \w+", s.strip()):
			return False
		# incidently, I am going to default to True
		return True
	
	def form_action(self, text):
		# form an action to the format;
		# starts with a capital letter and ends with a full stop.
		text = text[0].upper() + text[1:]
		if text[-1]!='.':
			text += '.'
		return text
	
	def form_describer(self, text):
		# form a describer according to the format;
		# begin with lowercase; not ending on a full stop.
		try:
			text = text[0].lower() + text[1:]
		except IndexError:
			return None
		if text[-1]!='.':
			text = text.strip('.')
		return text
	
	def clean_infostring(self, text):
		text = text.strip()
		text = text.strip("''")
		text = text.strip()
		return text
	
	def clean_dialoguestring(self, text):
		text = text.strip()
		if re.search(r" '$", text) or re.match(r"' ", text):
			text = text.strip("' ")
		text = text.lstrip(':')
		if text == "'":
			return None
		return text.strip()
	
	def handle_rawspeech(self, text, speaker):
		strings = []
		raction = re.compile("(('')?[^\[]\[|('')?\(|^[\[\(])([^\]\)]+)(\][^\]]('')?|\)('')?|[\]\)]$)")
		lines = text.split("\n")
		i = 0
		for l in lines:
			if i > 0:
				strings.append((self.LINEFEED, None))
			if raction.search("  %s  " % l):
				isAction = False
				for s in raction.split(l):
					if s == None:
						continue
					t = s.strip("''").strip("' ")
					if t in ['[', '('] and not isAction:
						isAction = True
						continue
					if t in [']', ')'] and isAction:
						isAction = False
						continue
					if isAction:
						if self.is_talk_describer(s):
							d = self.form_describer(self.clean_infostring(s))
							if d != None:
								strings.append((self.TALKDESCRIBER, d))
						else:
							strings.append((self.ACTION, self.form_action(self.clean_infostring(s))))
					else:
						if s not in ['', '.']:
							cs = self.clean_dialoguestring(s)
							if cs != None:
								strings.append((self.TALK, cs))
			else:
				strings.append((self.TALK, self.clean_dialoguestring(l)))
			i += 1
		return strings
	
	def handle_dialogue(self, text):
		# note; text must be line splitted by this point.
		# each line is assume to be a line in the dialogue.
		dialogueparse = []
		for line in text.splitlines():
			rspeaker = re.compile("^'''(.*?)'''")
			speech = ''
			try:
				speaker = rspeaker.search(line).group(1).strip(': ')
			except AttributeError:
				# it could be an additional line to the former speech, so let's
				# add it to that.
				try:
					dialogueparse[-1]['speech'] += "\n%s" % line
					continue
				except IndexError:
					dialogueparse.append({'speaker' : None, 'speech': line})
					continue
			speech += rspeaker.sub('', line).lstrip(': ')
			dialogueparse.append({'speaker' : speaker, 'speech' : speech.strip()})
		dialogue = []
		for d in dialogueparse:
			dialogue.append({'speaker' : d['speaker'], 'speech' : self.handle_rawspeech(d['speech'], d['speaker'])})
		return dialogue
	
	def poem_parse(self):
		# while it probably sane, let's not assume it is, we do some quick
		# checks on whether <poem> matches the amount of </poem> and whether
		# they come in an ababab format.
		try:
			xml = etree.fromstring("<m>%s</m>" % self.content.replace('&', '&amp;') )
		except etree.XMLSyntaxError:
			self.content = "%s\n%s" % ("<!-- Bot comment: This or these quote(s)'s syntax are unsane.  Please fix them. -->", self.content)
			self.log('			> Poem elements syntax error.')
			return False
		for poem in xml:
			for child in poem:
				if child.tag == 'poem':
					# unsane in our world, let's bail.
					self.content = "%s\n%s" % ("<!-- Bot comment: This or these quote(s)'s syntax are unsane.  Please fix them. -->", self.content)
					self.log('			> Poem contains a poem.')
					return False
		# okay, still here?  Then we must be doing something right.
		for poem in xml:
			if poem.tag != 'poem':
				continue
			dialogue = self.handle_dialogue(poem.text)
			if dialogue==None:
				self.content = "%s\n%s" % ("<!-- Bot comment: This or these quote(s)'s syntax are unsane.  Please fix them. -->", self.content)
				self.log('			> No dialogue returned after handling it.')
				return False
			self.dialogues.append(dialogue)
		# let's find the top and the bottom, okay?
		rsides = re.compile(r"\{\{q\|.*?\n\|?[2-9]?\}\}", re.S | re.I | re.M)
		f = rsides.split(self.content)
		try:
			self.top = f[0]
			self.bottom = f[1]
		except IndexError:
			return False
		# let's find the columns
		rcol = re.compile("^\|([^\}]*)\}\}", re.M)
		try:
			col = rcol.search(self.content).group(1)
			self.columns = int(col)
		except (AttributeError, ValueError):
			self.columns = 1
		if self.columns == 1 and len(self.dialogues) > 10:
			self.columns = 2
		return True
	
	def list_parse(self):
		rsplit = re.compile("^\*(.*?)$", re.M)
		rbr = re.compile("<br([^>]*)>", re.I)
		bottom = ''
		top = ''
		somethingParsed = False
		for line in self.content.splitlines():
			if line.strip()=='':
				continue
			if line[0]!='*':
				if somethingParsed:
					bottom += line
				else:
					top += line
				continue
			line = line.strip('* \n')
			dialogue = self.handle_dialogue(rbr.sub("\n", line))
			if dialogue == None:
				self.content = "%s\n%s" % ("<!-- Bot comment: This or these quote(s)'s syntax are unsane.  Please fix them. -->", self.content)
				self.log('			> No dialogue returned after handling it.')
				return False
			self.dialogues.append(dialogue)
			somethingParsed = True
		self.top = top
		self.bottom = bottom
		return True		
	
	def parse(self):
		r = re.compile(r'\{\{q\|', re.I)
		if r.search(self.content):
			if not self.poem_parse():
				return # something broke, bail
		else:
			r = re.compile(r"^\*[^']*'''", re.M)
			if r.search(self.content):
				if not self.list_parse():
					return # something broke, bail
			else:
				return # nothing to parse
		self.render()
	
	def make_line(self, dialogue, text):
		text = text.strip()
		if dialogue['speaker']==None:
			line = '%s' % text
		else:
			line = "'''%s''': %s" % (dialogue['speaker'], text)
		return line.strip()
	
	def render(self):
		if len(self.dialogues) < 1:
			return # no dialogues?  I guess there is no content then
		s = ''
		for dialogue in self.dialogues:
			lines = []
			for d in dialogue:
				tmp = ''
				for w in d['speech']:
					if w[0]==self.TALK:
						tmp += w[1].strip()
					if w[0]==self.ACTION:
						tmp += " ''[%s]'' " % w[1]
					if w[0]==self.TALKDESCRIBER:
						tmp += " [%s] " % w[1]
					if w[0]==self.LINEFEED:
						lines.append(self.make_line(d, tmp))
						# set up something fake
						# I suppose this could be done prettier.
						d = {'speaker' : None}
						tmp = ''
				lines.append(self.make_line(d, tmp))
			tmp = ''
			for line in lines:
				tmp = "%s%s\n" % (tmp, line)
			s = "%s\n<poem>%s</poem>" % (s, tmp.strip())
		s = s.strip()
		add = ''
		if self.columns > 1:
			add = '|%s' % self.columns
		self.content = "%s\n{{q|\n%s\n%s}}\n%s" % (self.top, s, add, self.bottom)
		self.content = self.content.strip().replace('&amp;', '&')
	
	def get_content(self):
		return self.content
	
	def __init__(self, content):
		Basic.__init__(self, False, None, False)
		self.dialogues = []
		# Remember, content is assumed to be the section we are editing
		# therefore, if given a whole article, it will behave strange.
		self.content = content 
		self.parse()

# Quote functions

def has_quote_section(content):
	return re.search("^={2,3}\W*(Highlights / )?Quotes\W*={2,3}", content, re.I | re.M)

def get_quote_section(content):
	section = ''
	inquote = False
	incomment = False
	for line in content.splitlines():
		if re.search("<!--", line):
			incomment = True
		if re.search("-->", line):
			incomment = False
		if inquote:
			if re.match("={2,3}", line, re.I) and not incomment:
				section = "%s\n" % section
				inquote = False
			else:
				section = "%s%s\n" % (section, line)
		if re.match("={2,3}\W*(Highlights / )?Quotes\W*={2,3}", line, re.I) and not incomment:
			inquote = True
	if section.strip() == '':
		return None
	return section.strip()
