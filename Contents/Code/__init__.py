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
	ObjectContainer.title1 = PLUGIN_TITLE
	ObjectContainer.art = R(ART)
	ObjectContainer.view_group = 'List'

	DirectoryObject.thumb = R(ICON)
	DirectoryObject.art = R(ART)
	VideoClipObject.thumb = R(ICON)

	# Configure HTTP Cache lifetime
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13"

####################################################################################################

def MainMenu():
	oc = ObjectContainer()
	for show in HTML.ElementFromURL(BASE_URL+'/shows').xpath("//div[@id='all-shows-accordion']//div[@class='header']/span[@class='has-video']/preceding-sibling::span"):
		showVideos = show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/div[@class="info"]//a[@class="watch more"]')[0].get('href')
		if show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/ul[@class="nav"]/li')[0].text != None:
			oc.add(DirectoryObject(
				key = Callback(GetVideos, path = showVideos), 
				title = show.text))
		else:
			showMainPage = show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/ul[@class="nav"]/li/a[@class="more"]')[0].get('href')
			oc.add(DirectoryObject(
				key = Callback(GetVideos, path = showVideos, showMainPage = showMainPage), 
				title = show.text,
				art = Callback(GetBackground, path = showMainPage)))
	return oc

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

def GetVideos(path, showMainPage = None):
	if showMainPage != None:
		oc = ObjectContainer(view_group = "InfoList", art = Callback(GetBackground, path=showMainPage))
	else:
		oc = ObjectContainer(view_group = "InfoList")

	page = HTTP.Request(BASE_URL+path).content
	mrssdata = re.search('mrssData =[ ]+"([^"]+)', page).group(1)
	mrssdata =  String.Unquote(b64decode(mrssdata)).replace('media:','media-')

	for category in XML.ElementFromString(mrssdata).xpath("//item"):
		video_url = category.xpath('./link')[0].text +'#'+ category.xpath('./media-category')[0].text

		title = category.xpath('./title')[0].text
		summary = category.xpath('./description')[0].text
		thumb = category.xpath('./media-thumbnail')[0].get('url')
		duration = int(category.xpath('./media-content')[0].get('duration')) * 1000
		Log("IABI:" + video_url)
		oc.add(VideoClipObject(
	        url = video_url,
	        title = title,
	        summary = summary,
	        thumb = Callback(GetThumb, path = thumb),
	        duration = duration))

	if len(oc) == 0:
		return MessageContainer("No Videos", "There aren't any videos available for this show")
	return oc

####################################################################################################

def GetThumb(path, thumb_type = "image/jpeg"):
	if (path != None):
		try:
			return DataObject(HTTP.Request(path, cacheTime=CACHE_1MONTH), thumb_type)
		except:
			pass

	return Redirect(R(ICON))
