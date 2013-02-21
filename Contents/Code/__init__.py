# -*- coding: utf-8 -*-
NAME = "History Channel"
ICON = "icon-default.png"
ART = "art-default.jpg"
BASE_URL = "http://www.history.com"

####################################################################################################
def Start():

	Plugin.AddPrefixHandler("/video/historychannel", MainMenu, NAME, ICON, ART)

	Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
	Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")

	ObjectContainer.title1 = NAME
	ObjectContainer.art = R(ART)
	ObjectContainer.view_group = 'List'

	DirectoryObject.thumb = R(ICON)
	DirectoryObject.art = R(ART)
	VideoClipObject.thumb = R(ICON)

	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:12.0) Gecko/20100101 Firefox/12.0'

####################################################################################################
def MainMenu():
	oc = ObjectContainer()

	oc.add(DirectoryObject(key=Callback(FullShowsList), title="Shows With Full Episodes"))
	oc.add(DirectoryObject(key=Callback(AllShowsList), title="All Shows"))

	return oc

####################################################################################################
def FullShowsList():

	oc = ObjectContainer()

	for show in HTML.ElementFromURL(BASE_URL+'/videos').xpath('//div[@id="full-episode-area"]//div'):
		url = show.xpath('.//p/a/@href')[0].replace('\n','').replace('http://www.history.com','')
		title = show.xpath('.//p/a/text()')[0]
		thumb_url = BASE_URL + show.xpath('.//a/img/@src')[0]
		
		oc.add(DirectoryObject(
			key = Callback(GetVideos, path = url),
			title = title, 
			thumb = Resource.ContentsOfURLWithFallback(thumb_url,'icon-default.png')
		))

	return oc

####################################################################################################
def AllShowsList():

	oc = ObjectContainer()

	for show in HTML.ElementFromURL(BASE_URL+'/shows').xpath("//span[@class='has-video']/preceding-sibling::span"):
		showVideos = show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/div[@class="info"]//a[@class="watch more"]')[0].get('href')
		try: showMainPage = show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/ul[@class="nav"]/li/a[@class="more"]')[0].get('href')
		except: showMainPage = showVideos

		oc.add(DirectoryObject(
			key = Callback(GetVideos, path = showVideos, showMainPage = showMainPage),
			title = show.text
		))

	return oc

####################################################################################################
def GetVideos(path, showMainPage = None, isNestedPlaylist = False):

	url = BASE_URL + path
	oc = ObjectContainer(view_group = "InfoList")
	page = HTTP.Request(url).content
	html = HTML.ElementFromString(page)
	playlists = html.xpath('//li[contains(@class,"parent videos")]/ul/li/a')

	if playlists and not isNestedPlaylist:
		for playlist in playlists:
			oc.add(DirectoryObject(
				key = Callback(GetVideos, path = playlist.get('href'), showMainPage = showMainPage, isNestedPlaylist = True),
				title = playlist.text
			))
	else:
		pl = page[page.find('playlist = ')+11:]
		pl = pl[:pl.find(';\n</script')]
		playlistJSON = JSON.ObjectFromString(pl)

		for video in playlistJSON:
			oc.add(VideoClipObject(
				url = video['siteUrl'],
				title = video['display']['title'],
				duration = int(video['display']['duration']) * 1000,
				summary = video['display']['description'],
				thumb = video['display']['thumbUrl']
			))

	if len(oc) == 0:
		return MessageContainer("No Videos", "There aren't any videos available for this show")
	return oc

####################################################################################################
def TimeToMs(timecode):

	seconds = 0

	try:
		duration = timecode.split(':')
		duration.reverse()

		for i in range(0, len(duration)):
			seconds += int(duration[i]) * (60**i)
	except:
		pass

	return seconds * 1000