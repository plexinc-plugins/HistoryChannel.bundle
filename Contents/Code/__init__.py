# -*- coding: utf-8 -*-
from base64 import b64decode
'''
Created on December 1, 2010

Version: 0.1
Author: by Pierre
'''

# Plugin parameters
PLUGIN_TITLE = "History Channel"
PLUGIN_PREFIX = "/video/HistoryChannel"
MEDIA = {'media':'http://search.yahoo.com/mrss'}

# Art
ICON = "icon-default.png"
ART = "art-default.jpg"
BACKUPART = "art-backup.jpg"
PREFS = "icon-prefs.png"

#Some URLs for the script
BASE_URL = "http://www.history.com"

USER_AGENT = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.12) Gecko/20101026 Firefox/3.6.12'

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
	
	HTTP.CacheTime = 0
	HTTP.Headers['User-Agent'] = USER_AGENT

####################################################################################################
# The plugin's main menu. 

def MainMenu():

    dir = MediaContainer(art = R(ART), viewGroup = "List")
    #Log(HTTP.Request(BASE_URL).content)
    for show in HTML.ElementFromURL(BASE_URL+'/shows').xpath("//div[@id='all-shows-accordion']//div[@class='header']/span[@class='has-video']/preceding-sibling::span"):
      #Log(show.text)
      showVideos = show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/div[@class="info"]//a[@class="watch more"]')[0].get('href')
      #Log(showVideos)
      Log(show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/ul[@class="nav"]/li')[0].text)
      if show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/ul[@class="nav"]/li')[0].text != None:
            dir.Append(Function(DirectoryItem(getVideos, title=show.text, thumb=R(ICON),art=R(ART)),path=showVideos))
      else:  
        showMainPage = show.xpath('./parent::div/following-sibling::div[@class="content clearfix"]/ul[@class="nav"]/li/a[@class="more"]')[0].get('href')
        Log(showMainPage)
        dir.Append(Function(DirectoryItem(getVideos, title=show.text, thumb=R(ICON),art=Function(getBackground, path=showMainPage)),path=showVideos))
    return dir
    
def getBackground(path):
  Log(path)
  try :
    page = HTTP.Request(BASE_URL+path).content
    bkgnd= page[page.find('background: url(')+16:]
    bkgnd = bkgnd[:bkgnd.find(')')]
    Log(bkgnd)
    
    logo = HTML.ElementFromString(page).xpath('//div[@class="logo"]//img')[0].get('src')
    Log(logo)
    if logo == None:
      return DataObject(HTTP.Request('http://www.plexapp.tv/plugins/history/?image='+bkgnd),'image/jpeg')
    else:
      return DataObject(HTTP.Request('http://www.plexapp.tv/plugins/history/?image='+bkgnd+'&logo='+logo),'image/jpeg')
  except:
    return Redirect(R(BACKUPART))
    
def getShow(sender,path):
    dir = MediaContainer(art = R(ART), viewGroup = "List")
    for category in HTML.ElementFromURL(BASE_URL+path).xpath("//li[@class='parent videos']/ul/li/a"):
      dir.Append(Function(DirectoryItem(getVideos, title=category[1], thumb=R(ICON)),title = category[1], link = (CATEGORY_URL%(category[0],Prefs['Videosperpage'])), page = 1))

    return dir

def getVideos(sender,path):
    dir = MediaContainer(art = R(ART), viewGroup = "InfoList")
    page = HTTP.Request(BASE_URL+path).content
    mrssdata = page[page.find('mrss: \"')+7:]
    mrssdata =  String.Unquote(b64decode(mrssdata[:mrssdata.find('\"')])).replace('media:','media-')
#    Log(mrssdata)
    for category in XML.ElementFromString(mrssdata).xpath("//item"):
    
      Videourl = category.xpath('./link')[0].text +'#'+ category.xpath('./media-category')[0].text
      duration = int(category.xpath('./media-content')[0].get('duration'))*1000
      #Log(Videourl)
      dir.Append(Function(VideoItem(PlayVideo, summary = category.xpath('./description')[0].text, duration=duration, title=category.xpath('./title')[0].text, thumb=Function(GetThumb, path=category.xpath('./media-thumbnail')[0].get('url'))),path=Videourl))

    return dir
####################################################################################################
def PlayVideo(sender, path):
	return Redirect(WebVideoItem(path)) 

def GetThumb(path,thumb_type = "image/jpg"):
	if (path == None):
		return R(ICON)
	return DataObject(HTTP.Request(path),thumb_type) 	

def ParseCategoryXML(sender, title, link, page):
	dir = MediaContainer(art = R(ART), viewGroup = "InfoList", title2 = title, replaceParent = (page>1))
	
	if page>0:
		locallink = link + str(int(Prefs['Videosperpage'])*(page-1)+1)
		Log(locallink)
	else:
		locallink = link

	xmlfeed = XML.ElementFromURL(locallink,encoding = "iso-8859-1")
	
	if (page>1):
		dir.Append(Function(DirectoryItem(ParseCategoryXML, title="Vorhergehende Seite"),title =title, link = link , page = page - 1))
	
	for video in xmlfeed.xpath("//playlist/listitem"):
		id = video.xpath("videoid")[0].text
		title = video.xpath("headline")[0].text.encode("utf-8")
		try:
  		  summary = video.xpath("teaser")[0].text.encode("utf-8")
		except: 
		  summary = HTML.StringFromElement(video,encoding = "iso-8859-1")
  		  summary = summary[summary.find('<teaser>')+8:]
		  summary = summary[:summary.find('<')].encode("utf-8")

		try: 
		  thumbpath = video.xpath("thumb")[0].text
		except: 
		  thumbpath = ''
		  
		try:
	  	  duration = video.xpath("playtime")[0].text.split(':')
	  	  if len(duration) == 3:
		    duration = (int(duration[0])*3600 + int(duration[1])*60 + int(duration[2]))*1000 
	  	  else:
		    duration = (int(duration[0])*60 + int(duration[1]))*1000
		except:
		  duration = 0
		  
		Log(duration)

		if Prefs['ShowAllRes'] == "Alle" :
			dir.Append(Function(DirectoryItem(ParseVideoXML, title=title, summary = summary, duration = duration, thumb=Function(GetThumb,path = thumbpath)),title =title, summary = summary, thumbpath = thumbpath, link = (VIDEOXML_URL%id)))
		else:
			maxres = 0
			url = None	
			xmlfeed = XML.ElementFromURL((VIDEOXML_URL%id),encoding = "iso-8859-1")
			for streams in xmlfeed.xpath("//encodings"):
				for stream in streams:
					filename = stream.xpath("filename")[0].text
					extension = filename[filename.find('.')+1:]

					if (extension=="mp4" or extension=="flv"):
						currentres = int(stream.xpath("width")[0].text) + int(stream.xpath("height")[0].text)
						if (currentres >= maxres):
							maxres = currentres
							url = VIDEOFILE_URL % stream.xpath("filename")[0].text
			if (url != None):
				dir.Append(VideoItem(url, title=title, summary=summary, duration = duration, thumb=Function(GetThumb,path=thumbpath))) 

	if (page>0):
		#nextpage = ("Nächste Seite").decode("iso-8859-1").encode("utf-8")
		dir.Append(Function(DirectoryItem(ParseCategoryXML, title="Nächste Seite"),title = title, link = link , page = page + 1)) #ä
	return dir     

def ParseVideoXML(sender, title, summary, duration, thumbpath, link):
	dir = MediaContainer(art = R(ART), viewGroup = "List", title2 = title)
	Log(link)
	xmlfeed = XML.ElementFromURL(link,encoding = "iso-8859-1")

	for streams in xmlfeed.xpath("//encodings"):
		for stream in streams:
			width = stream.xpath("width")[0].text
			height = stream.xpath("height")[0].text
			filename = stream.xpath("filename")[0].text

			url = VIDEOFILE_URL % filename
			extension = filename[filename.find('.')+1:]
			thistitle = title + " - " + width + "x" + height + " - " + extension
			if (extension=="mp4" or extension=="flv"):
				dir.Append(VideoItem(url, title=thistitle, summary=summary, duration = duration, thumb=Function(GetThumb,path=thumbpath))) 
	return dir