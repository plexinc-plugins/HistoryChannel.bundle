TITLE = 'History Channel'
PREFIX = '/video/historychannel'

SHOWS = 'http://wombatapi.aetv.com/shows2/history'

####################################################################################################
def Start():

    ObjectContainer.title1 = TITLE
    HTTP.CacheTime = CACHE_1HOUR
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11) AppleWebKit/601.1.56 (KHTML, like Gecko) Version/9.0 Safari/601.1.56'

####################################################################################################
@handler(PREFIX, TITLE)
def MainMenu():
    oc = ObjectContainer()
    
    json_data = JSON.ObjectFromURL(SHOWS)
    
    for item in json_data:
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
    
    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are no shows available.')
    else:
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
        
        url = item['siteUrl']
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
    
    return oc
