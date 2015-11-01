TITLE = 'History Channel'
PREFIX = '/video/historychannel'

SHOWS = 'http://wombatapi.aetv.com/shows2/history'
SIGNATURE_URL = 'http://servicesaetn-a.akamaihd.net/jservice/video/components/get-signed-signature?url=%s'
SMIL_NS = {"a":"http://www.w3.org/2005/SMIL21/Language"}

####################################################################################################
def Start():

    ObjectContainer.title1 = TITLE
    HTTP.CacheTime = CACHE_1HOUR
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11) AppleWebKit/601.1.56 (KHTML, like Gecko) Version/9.0 Safari/601.1.56'

####################################################################################################
@handler(PREFIX, TITLE)
def MainMenu():
    oc = ObjectContainer()
    
    oc.add(
        DirectoryObject(
            key = Callback(Shows, title='History Channel Shows', network='History'),
            title ='History Channel Shows'
        )
    )
     
    oc.add(
        DirectoryObject(
            key = Callback(Shows, title='History Channel 2 Shows', network='H2'),
            title ='History Channel 2 Shows'
        )
    ) 
    # Pull the full episode carousel id so it will not cause errors if it changes
    #carousel_id=HTML.ElementFromURL(BASE_URL).xpath('//h2[text()="Full Episodes"]/parent::div//@id')[0].split('_')[0]
    #oc.add(DirectoryObject(key=Callback(Videos, title='Full Episodes', show_url=BASE_URL, carousel_id=carousel_id), title='Full Episodes')) 
    return oc

####################################################################################################
@route(PREFIX + '/shows')
def Shows(title, network):
    oc = ObjectContainer(title2=title)
    
    json_data = JSON.ObjectFromURL(SHOWS)
    
    for item in json_data:
        if not network == item['network']:
            continue
            
        if not (item['hasNoVideo'] == 'false' or item['hasNoHDVideo'] == 'false'):
            continue
        
        oc.add(
            TVShowObject(
                key = Callback(
                    Seasons,
                    show_id = item['showID'],
                    show_title = item['detailTitle'],
                    episode_url = item['episodeFeedURL'],
                    clip_url = item['clipFeedURL'],
                    show_thumb = item['detailImageURL2x']
                ),
                rating_key = item['showID'],
                title = item['detailTitle'],
                summary = item['detailDescription'],
                thumb = item['detailImageURL2x'],
                studio = item['network']
            )
        )

    oc.objects.sort(key = lambda obj: obj.title)
    
    return oc

####################################################################################################
@route(PREFIX + '/seasons')
def Seasons(show_id, show_title, episode_url, clip_url, show_thumb):

    oc = ObjectContainer(title2=show_title)
    
    json_data = JSON.ObjectFromURL(episode_url + '&filter_by=isBehindWall&filter_value=false')
    
    seasons = {}
    for item in json_data['Items']:
        if 'season' in item:
            if not int(item['season']) in seasons:
                seasons[int(item['season'])] = 1
            else:
                seasons[int(item['season'])] = seasons[int(item['season'])] + 1
    
    Log(seasons)
    for season in seasons:
        oc.add(
            SeasonObject(
                key = Callback(
                    Episodes,
                    show_title = show_title,
                    episode_url = episode_url,
                    clip_url = clip_url,
                    show_thumb = show_thumb,
                    season = season
                ),
                title = 'Season %s' % season,
                rating_key = show_id + str(season),
                index = int(season),
                episode_count = seasons[season],
                thumb = show_thumb
            )
        )
 
    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='This show does not have any unlocked videos available.')
    else:
        oc.objects.sort(key = lambda obj: obj.index, reverse = True)
        return oc 
    

####################################################################################################
@route(PREFIX + '/episodes')
def Episodes(show_title, episode_url, clip_url, show_thumb, season):

    oc = ObjectContainer(title2=show_title)
    json_data = JSON.ObjectFromURL(episode_url + '&filter_by=isBehindWall&filter_value=false')
    
    for item in json_data['Items']:
        if 'season' in item:
            if not int(item['season']) == int(season):
                continue
        
        url = item['playURL_HLS']
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
        duration = int(item['totalVideoDuration']) if 'totalVideoDuration' in item else None
        originally_available_at = item['originalAirDate'].split('T')[0] if 'originalAirDate' in item else None
        index = int(item['episode']) if 'episode' in item else None
        season = int(item['season']) if 'season' in item else None
        
        oc.add(
            CreateEpisodeObject(
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
    
    return oc

###################################################################################################
@route(PREFIX + '/createepisodeobject', duration=int, index=int, season=int, include_container=bool)
def CreateEpisodeObject(url, title, summary, thumb, art, show, duration, originally_available_at, index, season, include_container=False):

    episode_obj = EpisodeObject(
        key = 
            Callback(
                CreateEpisodeObject,
                url = url,
                title = title,
                summary = summary,
                thumb = thumb,
                art = art,
                show = show,
                duration = duration,
                originally_available_at = originally_available_at,
                index = index,
                season = season,
                include_container = True
            ),
        rating_key = url,
        title = title,
        summary = summary,
        thumb = thumb,
        art = art,
        show = show,
        duration = duration,
        originally_available_at = Datetime.ParseDate(originally_available_at).date() if originally_available_at is not None else None,
        index = index,
        season = season,
        items = [
            MediaObject(
                parts=[PartObject(key=HTTPLiveStreamURL(Callback(PlayVideo, url=url)))],
                audio_channels = 2,
                optimized_for_streaming = True,
                video_resolution = 540
            )
        ]
    )
    
    if include_container:
        return ObjectContainer(objects=[episode_obj])
    else:
        return episode_obj

###################################################################################################
@route(PREFIX + '/playvideo.m3u8')
@indirect
def PlayVideo(url, **kwargs):

    unsigned_smil_url = url.split('?')[0]
    signature = HTTP.Request(SIGNATURE_URL % String.Quote(unsigned_smil_url)).content
    smil_url = '%s?switch=hls&assetTypes=medium_video_ak&mbr=true&metafile=true&sig=%s' % (unsigned_smil_url, signature)
    smil = XML.ElementFromURL(smil_url)

    # Check for expired
    expired = smil.xpath('//*[@*[contains(., "Expired") or contains(., "expired")]]')
    if len(expired) > 0:
        raise Ex.MediaExpired
    
    max_resolution = 0
    hls_url = None
    for video in smil.xpath('//a:video', namespaces=SMIL_NS):
        resolution = video.get('height')
        if resolution > max_resolution:
            max_resolution = resolution
            hls_url = video.get('src')
            break
            
    if not hls_url:
        raise Ex.MediaNotAvailable
        
    return IndirectResponse(
        VideoClipObject,
        key = HTTPLiveStreamURL(url=hls_url)
    )
