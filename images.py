# -*- encoding: utf-8 -*-

from basic import Basic
from logindata import userdata
import re

class Images(Basic):

	imageapi = None
	usable = False
	
	def getImages(self, time):
		images = self.imageapi.get_recentchanges(200, time, "6")
		if len(images) > 0:
			return images
		self.log("No images found since %s, using 10 random images instead." % time)
		return self.imageapi.get_list(10, "6")
	
	def moveToPoolWiki(self, image):
		pass
	
	def routine_job(self, time):
		if not self.usable:
			self.log("Log in failed")
			return False
		images = self.getImages(time)
		for image in images:
			self.log("Handling image `%s'..." % image['title'])
			description = work = self.imageapi.get_content(image['title'])
			imageinfo = self.imageapi.get_image(image['title'])
			capture = False
			if float(imageinfo["height"])/imageinfo["width"] == 9/16.0:
				# 16:9?  Sounds likely to be a Futurama screen capture.
				# though we should probably check for other shows.
				if not re.search("\{\{Futurama screen cap", work, re.I) and not re.search("\{\{Futurama cropped screen cap", work, re.I) and not re.search("\{\{Futurama comic scan", work, re.I) and not re.search("\{\{Futurama promo", work, re.I) and not re.search("\{\{Futurama storyboard", work, re.I) and not re.search("\{\{Non-Futurama screen cap", work, re.I) and not re.search("\{\{Original work", work, re.I) and not re.search("\{\{Fan photo", work, re.I) and not re.search("\{\{Derived Futurama work", work, re.I):
					self.log("\t * Assuming it is an unregistered capture")
					work = "%s\n== Licensing ==\n{{Futurama screen cap}}" % work
					capture = True
				if re.search("\{\{Futurama screen cap", work, re.I):
					capture = True
				if imageinfo["height"] < 720 and capture:
					work = "{{low resolution}}\n%s" % work
				if imageinfo["height"] > 720 and capture:
					# larger than 720?  Something's wrong!
					work = "{{bad quality}}\n%s" % work
			if re.search(".*\.jpe?g$", image['title']):
				if re.search("\{\{Futurama[^\}]*screen cap\}\}", work, re.I) and not re.search("\{\{(jpg to png|png exist)", work, re.I):
					self.log("\t * Futurama screen capture in JPEG")
					work = "{{jpg to png}}\n%s" % work
					
			if description != work:
				self.log("\t > Changes made, committing an edit")
				self.imageapi.edit_page(image['title'], work, "Bot edit with recommendations, etc.")
			else:
				self.log("\t > No changes made, ommitting an edit")
	
	def __init__(self, debug, api, verbose, poolapi):
		Basic.__init__(self, debug, api, verbose)
		self.imageapi = poolapi
		if self.imageapi.login(userdata.username, userdata.password):
			self.log("Logged in to Pool wiki succesful.")
			self.usable = True
		else:
			self.log("Failed to log into Pool wiki; image operations will not be available in this run.")
