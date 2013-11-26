TITLE = 'History Channel'
PREFIX = '/video/historychannel'

BASE_URL = "http://www.history.com"
H_SHOWS = "http://www.history.com/videos"
H2_SHOWS = "http://www.history.com/videos/h2"
# We pull the url for the show for the code below from the web page using regex
# Ex http://www.history.com/api/html/shows/pawn-stars/videos?co=true&m=5189717d404fa&s=All&free=false
API_URL = 'http://www.history.com%s?co=true&m=%s&s=All&free=false'
RE_CAROUSEL_ID = Regex("div id='(.+?)'><!--")
RE_CAROUSEL_NAME = Regex('class="head-section1">(.+?)<')
RE_API = Regex("freeFilter\[data-module-id=.+freefilter', '(.+?)'")
####################################################################################################
def Start():

    ObjectContainer.title1 = "Comedy Central"
    HTTP.CacheTime = CACHE_1HOUR
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:18.0) Gecko/20100101 Firefox/18.0'

####################################################################################################
@handler(PREFIX, TITLE)
def MainMenu():
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(Types, title='History Channel Shows', url=H_SHOWS), title='History Channel Shows')) 
    oc.add(DirectoryObject(key=Callback(Types, title='History Channel 2 Shows', url=H2_SHOWS), title='History Channel 2 Shows')) 
    # Pull the full episode carousel id so it will not cause errors if it changes
    carousel_id=HTML.ElementFromURL(BASE_URL).xpath('//h2[text()="Full Episodes"]/parent::div//@id')[0].split('_')[0]
    oc.add(DirectoryObject(key=Callback(Videos, title='Full Episodes', show_url=BASE_URL, carousel_id=carousel_id), title='Full Episodes')) 
    return oc
####################################################################################################
@route(PREFIX + '/types')
def Types(url, title):
    oc = ObjectContainer()
    shows = HTML.ElementFromURL(url)
    for show in shows.xpath('//li[@class="item hasFullVideos"]'):
        name = show.xpath('./a//@alt')[0]
        if not name:
            name = show.xpath('.//@data-title')[0]
        show_url = show.xpath('./a//@href')[0]
        if not show_url.startswith('http://'):
            show_url = BASE_URL + show_url
        thumb = show.xpath('./a/img//@src')
        oc.add(DirectoryObject(key = Callback(TypeMenu, show_url=show_url, title=name, thumb=thumb), title=name, thumb=Resource.ContentsOfURLWithFallback(thumb)))

    return oc

####################################################################################################
@route(PREFIX + '/typemenu')
def TypeMenu(title, show_url, thumb):

    oc = ObjectContainer(title2=title)
    shows = HTML.ElementFromURL(show_url)

    for section in shows.xpath('//section/div/div/div[@class="span12"]/div'):
        try:
            title = section.xpath('./div/h4[@class="head-section1"]//text()')[0].strip()
        except:
            title = section.xpath('./div/h3//text()')[0].strip()
        carousel_id = section.xpath('.//@id')[0]
        oc.add(DirectoryObject(key = Callback(Videos, show_url=show_url, title=title, carousel_id=carousel_id), title=title, thumb=Resource.ContentsOfURLWithFallback(thumb)))

    return oc

####################################################################################################
@route(PREFIX + '/videos')
def Videos(show_url, title, carousel_id):

    oc = ObjectContainer(title2=title)

    show_content = HTTP.Request(show_url).content
    # Found that the main page no longer has a an api for its carousels. 
    # This will try to find the carousel api information in the page to produce carousels
    # If not, it will pull the carousel info straight from the html page
    try:
        show_api = RE_API.search(show_content).group(1)
        content = HTTP.Request(API_URL %(show_api, carousel_id)).content
        content = "[%s]" % content
        content_json = JSON.ObjectFromString(content)
        data = content_json[0][carousel_id]
        data = HTML.ElementFromString(data)
    except:
        data_section = HTML.ElementFromString(show_content).xpath('//div[contains(@id,"%s")]' %carousel_id)[0]
        raw_data = HTML.StringFromElement(data_section)
        data = HTML.ElementFromString(raw_data)
        
    for episode in data.xpath('//li[contains(@class,"slider-item")]/a'):
        url = episode.xpath('.//@data-href')[0]
        if not url.startswith('http://'):
            url = BASE_URL + url
        data_status = episode.xpath('.//@data-status')[0]
        title = episode.xpath('.//@data-original-title')[0]
        if data_status == 'locked':
            continue
        # Found one video with an empty duration, since it has to be in a try, putting whole pull there to be safe
        try:
            duration = episode.xpath('.//@data-duration')[0].replace('min', '')
            duration = int(duration) * 60000
        except:
            duration = 0
        # Some sections do not have a rating
        try:
            rating = episode.xpath('.//@data-rating')[0]
        except:
            rating = None
        try:
            thumb = episode.xpath('.//img//@src')[0]
        except:
            thumb = episode.xpath('.//img//@data-src')[0]
        description = episode.xpath('.//@data-content')[0]
        summary = HTML.ElementFromString(description).xpath('./p//text()')[0]

        oc.add(VideoClipObject(
            url = url,
            title = title,
            content_rating = rating,
            summary = summary,
            thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))

    if len(oc) < 1:
        return ObjectContainer(header="Empty", message="This show does not have any unlocked videos available.")
    else:
        return oc
