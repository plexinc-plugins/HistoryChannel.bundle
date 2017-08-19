TITLE = 'History Channel'
ART = 'art-default.jpg'
ICON = 'icon-default.jpg'
PREFIX = '/video/historychannel'

BASE_PATH = 'http://www.history.com'
SHOWS_URL = 'http://www.history.com/shows'
VIDEO_URL = 'http://www.history.com/videos'

EPISODES = 'https://mediaservice.aetndigital.com/SDK_v2/show_titles/episode/history?show_name=%s'
CLIPS = 'https://mediaservice.aetndigital.com/SDK_v2/show_titles/clip/history?show_name=%s'

RE_SEASEP =  Regex('S(\d+) E(\d+)')

####################################################################################################
def Start():

    ObjectContainer.title1 = TITLE
    HTTP.CacheTime = CACHE_1HOUR
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11) AppleWebKit/601.1.56 (KHTML, like Gecko) Version/9.0 Safari/601.1.56'

####################################################################################################
@handler(PREFIX, TITLE, art=ART, thumb=ICON)
def MainMenu():

    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(HTMLSection, title="Popular Shows", url=SHOWS_URL, section_type="popular-shows"), title="Popular Shows"))
    oc.add(DirectoryObject(key=Callback(HTMLSection, title="All Shows", url=SHOWS_URL, section_type="all-shows"), title="All Shows"))
    oc.add(DirectoryObject(key=Callback(HTMLSection, title="Recent Full Episodes", url=VIDEO_URL, section_type="most-recent-videos"), title="Recent Full Episodes"))

    return oc

####################################################################################################
# This function produces a list from the content section of the html
# Can produce show sections as well as video sections for full episodes or movies
@route(PREFIX + '/htmlsection')
def HTMLSection(title, url, section_type):

    oc = ObjectContainer(title2=title)
    data = HTML.ElementFromURL(url)

    for item in data.xpath('//div[contains(@data-module-id, "%s")]/ul/li/a' % (section_type)):

        # Skip any ads
        try: is_ad = item.xpath('./@data-module-id')[0]
        except: is_ad = ''

        if 'tile-promo' in is_ad:
            continue

        item_url = item.xpath('./@href')[0]
        if not item_url.startswith('http:'):
            item_url = BASE_PATH + item_url

        try: show_title = item.xpath('.//h4[@class="title"]/text()')[0]
        except: 
            # For shows that do not include a title, try to use URL to construct it
            try: show_title = item_url.split('/')[-1].replace('-', ' ').title()
            except: show_title = ''

        try: item_thumb = item.xpath('./img/@src')[0]
        except: item_thumb = None

        # For shows
        if url == SHOWS_URL:
            # Skip any All shows that do not include available episodes
            try: episodes = item.xpath('./div[@class="episodes "]//text()')[0]
            except: episodes = None

            if not episodes and not item_thumb:
                continue

            oc.add(
                DirectoryObject(key = Callback(Seasons, url = item_url, title = show_title),
                    title = show_title,
                    thumb = Resource.ContentsOfURLWithFallback(item_thumb)
                )
            )

        # For videos
        else:
            # Check for locked videos
            lock_code = item.xpath('./div[@class="circle-icon"]/span/@class')[0]
            if lock_code.endswith('key'):
                continue

            item_title = item.xpath('.//span[@class="meta"]/text()')[0]

            try: date = Datetime.ParseDate(item.xpath('.//p[@class="airdate"]/text()')[0].split('on ')[1])
            except: date = None

            seas_ep = RE_SEASEP.search(item_title)

            try: (season, episode) = seas_ep.group(1, 2)
            except: (season, episode) = (0, 0)

            oc.add(
                EpisodeObject(
                    show = show_title,
                    season = int(season),
                    index = int(episode),
                    url = item_url,
                    title = item_title,
                    originally_available_at = date,
                    thumb = Resource.ContentsOfURLWithFallback(url=item_thumb)
                )
            )

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no unlocked videos to display right now.") 
    else:
        return oc

####################################################################################################
@route(PREFIX + '/seasons')
def Seasons(title, url):

    oc = ObjectContainer(title2=title)

    # Pull the proper values for thumb and title from show page for json URL	
    thumb = HTML.ElementFromURL(url, cacheTime=CACHE_1MONTH).xpath('//meta[@property="og:image"]/@content')[0]	

    try: title = HTML.ElementFromURL(url, cacheTime=CACHE_1MONTH).xpath('//meta[@name="aetn:SeriesTitle"]/@content')[0]	
    except: title = title	

    # Pull the seasons from the episode json	
    episode_url = EPISODES % (String.Quote(title, usePlus=False))
    json_content = HTTP.Request(episode_url + '&filter_by=isBehindWall&filter_value=false').content
    json_data = JSON.ObjectFromString(json_content)

    seasons = []

    for item in json_data['Items']:
        if 'season' in item:
            if not int(item['season']) in seasons:
                seasons.append(int(item['season']))

    for season in seasons:
        oc.add(
            DirectoryObject(
                key = Callback(
                    Episodes,
                    show_title = title,
                    url = '%s&filter_by=season&filter_value=%s' % (episode_url, season),
                    show_thumb = thumb,
                    season = season
                ),
                title = 'Season %s' % (season),
                thumb = thumb
            )
        )

    if len(oc) < 1 and json_data['totalNumber'] > 0:
        oc.add(DirectoryObject(key=Callback(Episodes, show_title=title, url=episode_url + '&filter_by=isBehindWall&filter_value=false', show_thumb=thumb), title="All Episodes", thumb = thumb))

    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='This show does not have any unlocked videos available.')
    else:
        return oc 

####################################################################################################
@route(PREFIX + '/episodes')
def Episodes(show_title, url, show_thumb, season=None):

    oc = ObjectContainer(title2=show_title)
    json_data = JSON.ObjectFromURL(url)

    for item in json_data['Items']:
        if item['isBehindWall'] == 'true':
            continue

        # Found an item missing the siteUrl value
        try: url = item['siteUrl']
        except: continue

        title = item['title']
        summary = item['description'] if 'description' in item else None

        if 'thumbnailImage2xURL' in item:
            thumb = item['thumbnailImage2xURL']
        elif 'stillImageURL' in item:
            thumb = item['stillImageURL']
        elif 'modalImageURL' in item:
            thumb = item['modalImageURL']
        else:
            thumb = show_thumb

        show = item['seriesName'] if 'seriesName' in item else show_title

        # Fix URL service error for URLs that do not include a unique show folder/directory
        if '/shows/video/' in url:
            url = SHOWS_URL + show.lower().replace(' ', '-') + url.split('/shows')[1]

        # Fix URL service error for URLs that do not include a '/shows/' directory
        if not '/shows/' in url:
            url = SHOWS_URL + url.split('www.aetv.com/')[1]

        duration = int(item['totalVideoDuration']) if 'totalVideoDuration' in item else None
        originally_available_at = Datetime.ParseDate(item['originalAirDate'].split('T')[0]).date() if 'originalAirDate' in item else None
        index = int(item['episode']) if 'episode' in item else None
        season = int(item['season']) if 'season' in item else None

        oc.add(
            EpisodeObject(
                url = url,
                title = title,
                summary = summary,
                thumb = thumb,
                art = show_thumb,
                show = show,
                duration = duration,
                originally_available_at = originally_available_at,
                index = index,
                season = season
            )
        )

    oc.objects.sort(key = lambda obj: obj.index)

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no unlocked videos to display right now.") 
    else:
        return oc
