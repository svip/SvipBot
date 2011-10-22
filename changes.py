# -*- encoding: utf-8 -*-

import re
import difflib
from basic import Basic

class Changes(Basic):

	maximum = 500
	
	def get_changes(self):
		if self.ts != None:
			self.changes = self.api.get_recentchanges(self.maximum, self.ts, "0|4|14")
			if len(self.changes) == 0:
				self.log("No recent changes since %s; skipping..." % self.ts)
			else:
				self.log("Found %s recent changes since %s." % (len(self.changes), self.ts))
		else:
			if self.maximum>0:
				self.log("No escape time defined, getting the previous %s recent changes..." % self.maximum)
				self.changes = self.api.get_recentchanges(self.maximum, None, "0|4|14")
			else:
				self.log("No recent changes permitted; skipping...")
	
	def detect_spam_creation(self, content, title, anon):
		if not anon:
			return 0
		if re.match(".*?[^0-9][0-9]{1,2}$", title) and re.match("^\[\[(File|Image):.*?[0-9]{3,4}.jpg\|thumb\|\]\]", content, re.I):
			return 75000
		return 0

	def handle_changes(self):
		self.get_changes()
		if self.changes == None or len(self.changes) == 0:
			self.log("No recent changes found, skipping...")
			return
		evaluation = []
		for change in self.changes:
			self.log("Checking edit %s on `%s'..." % (change['revid'], change['title']))
			score = 0
			if change['type'] == 'edit':
				edit = self.api.get_edit(change['revid'], change['old_revid'])
			elif change['type'] == 'new':
				edit = self.api.get_edit(change['revid'], None)
				#self.log("Not sure how to handle edits of type `new'... yet, skipping.")
				score += self.detect_spam_creation(edit[1]['content'], change['title'], edit[1]['anon'])
				score += 100
				self.log("Gave edit score: %s" % score)
				evaluation.append({'revid' : change['revid'], 'score' : score, 'title' : change['title'], 'user': edit[1]['user']})
				continue
			else:
				self.log("Unknown edit type, `%s'..." % change['type'])
				continue
			if edit == None or edit[0]['content'] == None or edit[1]['content'] == None:
				continue
			sizematters = True
			# Time for some score marking.
			if edit[1]['anon']:
				score += 100
			else:
				user = self.api.get_user(edit[1]['user'])
				if 'sysop' in user['groups']:
					self.log("This is a sysop!  ESCAPE!")
					continue
				if 'autoconfirmed' in user['groups']:
					score -= 200
				else:
					score += 200
			if edit[1]['comment'] != '':
				score -= 100
				undocoms = ["undid", "undo", "reverted"]
				for undo in undocoms:
					if undo in edit[1]['comment'] or undo.capitalize() in edit[1]['comment']:
						score -= 1000
						sizematters = False
			if sizematters:
				sizediff = int(edit[1]['size'])-int(edit[0]['size'])
				if sizediff < 0:
					score += abs(sizediff)/2
				else:
					score += sizediff/3
			diff = difflib.ndiff(edit[0]['content'].splitlines(1), edit[1]['content'].splitlines(1))
			preline = ''
			t = False
			links = 0
			linesincommon = 0
			for line in diff:
				if line[0:2] == '? ':
					continue
				if line[0:2] == '  ':
					linesincommon += 1
				if line[0:2] == '- ':
					preline = line[2:].strip()
				if line[0:2] == '+ ':				
					line = line[2:].strip()
					# check for external links
					extlinks = re.findall("(\[http://[^ ]*?\]|\[http://[^ ]*? .*?\])", line, re.I)
					for ext in extlinks:
						if not ext in preline:
							score += 250 + 250*links
							links += 1
					# check for {{e}} stuff
					appearref = re.findall("\{\{(elink|clink)\|[^\}]*\}\}", line, re.I)
					for apr in appearref:
						score -= 250
					# appear fixing
					appearref = re.findall("\{\{e\|[^\}]*\}\}", line, re.I)
					for apr in appearref:
						score -= 250
						if "{{elink|" in preline:
							score -= 200
					# check for table stuff
					tableelements = re.findall("(\{\||\|-|\|\})", line)
					for tbe in tableelements:
						score -= 150
			r = re.compile("\#REDIRECT\:", re.I)
			if r.match(edit[0]['content']) or r.match(edit[1]['content']):
				score -= 1000
			elif linesincommon <= 2 and len(edit[0]['content'].splitlines(1)) > 10:
				score += 2500*(3-linesincommon)
			self.log("Gave edit score: %s" % score)
			evaluation.append({'revid' : change['revid'], 'score' : score, 'title' : change['title'], 'user': edit[1]['user']})
		self.log("Writing evaluation...")
		content = ''
		for e in evaluation:
			if e['score'] < 500 and e['score'] > -500:
				continue # restrict uninteresting scores to not be written.
			if e['score'] > 1000 or e['score'] < -1000:
				a = "'''"
			else:
				a = ''
			content += '* %s[http://theinfosphere.org/index.php?diff=prev&oldid=%s Edit %s on "%s"]: Score: %s%s\n' % (a, e['revid'], e['revid'], e['title'], e['score'], a)
		content = "%s\n%s" % (self.api.get_content('User:SvipBot/evaluation'), content)
		if self.api.edit_page('User:SvipBot/evaluation', content, 'Evaluation update.'):
			self.log("Evaluation written.")
		else:
			self.log("Failed writing evaluation.")
		
		self.log("Handling evaluation of edits...")
		for e in evaluation:
			if e['score'] > 50000:
				self.log("Score above 50000 for %s on `%s'..." % (e['revid'], e['title']))
				self.log("> Deleting page and blocking user...")
				if not self.api.delete_page(e['title'], "Bot assumed this edit to be bad, deleting it on grounds of vandalism."):
					self.log(">> Delete unsuccessful.")
				if not self.api.block_user(e['user'], "1 year", "Bot caught this user vandalising..."):
					self.log(">> Block unsuccessful.")

	def set_ts(self, ts):
		self.ts = ts

	def __init__(self, debug, api, verbose):
		Basic.__init__(self, debug, api, verbose)
