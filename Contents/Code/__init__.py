# -*- coding: utf-8 -*-
import re
from base64 import b64decode
'''
Created on December 1, 2010

Version: 0.1
Author: by Pierre
'''

# Plugin parameters
PLUGIN_TITLE = "History Channel"
PLUGIN_PREFIX = "/video/historychannel"

# Art
ICON = "icon-default.png"
ART = "art-default.jpg"

# Some URLs for the script
BASE_URL = "http://www.history.com"

####################################################################################################

def Start():
	# Register our plugins request handler
	Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, PLUGIN_TITLE, ICON, ART)

	# Add in the views our plugin will support
	Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
	Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")

	# Set up our plugin's container
	MediaContainer.title1 = PLUGIN_TITLE
	MediaContainer.viewGroup = "List"
	MediaContainer.art = R(ART)
	DirectoryItem.thumb = R(ICON)

	# Configure HTTP Cache lifetime
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13"

####################################################################################################

def MainMenu():
	dir = MediaContainer()
	for show in HTML.ElementFromURL(BASE_URL+'/shows').xpath("//div[@id='all-shows-accordion']//div[@class='header']/span[@class='has-video']/preceding-sibling::span"):
		showVideos = show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/div[@class="info"]//a[@class="watch more"]')[0].get('href')
		if show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/ul[@class="nav"]/li')[0].text != None:
			dir.Append(Function(DirectoryItem(GetVideos, title=show.text), path=showVideos))
		else:  
			showMainPage = show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/ul[@class="nav"]/li/a[@class="more"]')[0].get('href')
			dir.Append(Function(DirectoryItem(GetVideos, title=show.text, art=Function(GetBackground, path=showMainPage)), path=showVideos, showMainPage=showMainPage))
	return dir

####################################################################################################

def GetBackground(path):
	try:
		page = HTTP.Request(BASE_URL+path).content
		bkgnd = page[page.find('background: url(')+16:]
		bkgnd = bkgnd[:bkgnd.find(')')]

		logo = HTML.ElementFromString(page).xpath('//div[@class="logo"]//img')[0].get('src')
		if logo == None:
			return DataObject(HTTP.Request('http://www.plexapp.tv/plugins/history/?image='+bkgnd, cacheTime=CACHE_1MONTH), 'image/jpeg')
		else:
			return DataObject(HTTP.Request('http://www.plexapp.tv/plugins/history/?image='+bkgnd+'&logo='+logo, cacheTime=CACHE_1MONTH), 'image/jpeg')
	except:
		return Redirect(R(ART))

####################################################################################################

def GetVideos(sender, path, showMainPage=None):
	if showMainPage != None:
		dir = MediaContainer(viewGroup="InfoList", art=Function(GetBackground, path=showMainPage))
	else:
		dir = MediaContainer(viewGroup="InfoList")

	page = HTTP.Request(BASE_URL+path).content
	mrssdata = re.search('mrssData = "([^"]+)', page).group(1)
	mrssdata =  String.Unquote(b64decode(mrssdata)).replace('media:','media-')

	for category in XML.ElementFromString(mrssdata).xpath("//item"):
		video_url = category.xpath('./link')[0].text +'#'+ category.xpath('./media-category')[0].text
		duration = int(category.xpath('./media-content')[0].get('duration'))*1000
		dir.Append(Function(VideoItem(PlayVideo, summary = category.xpath('./description')[0].text, duration=duration, title=category.xpath('./title')[0].text, thumb=Function(GetThumb, path=category.xpath('./media-thumbnail')[0].get('url'))), path=video_url))

	if len(dir) == 0:
		return MessageContainer("No Videos", "There aren't any videos available for this show")
	return dir

####################################################################################################

def PlayVideo(sender, path):
	return Redirect(WebVideoItem(path))

####################################################################################################

def GetThumb(path, thumb_type="image/jpeg"):
	if (path != None):
		try:
			return DataObject(HTTP.Request(path, cacheTime=CACHE_1MONTH), thumb_type)
		except:
			pass

	return R(ICON)
