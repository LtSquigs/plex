ART = 'art-default.png'
ICON = 'icon-default.png'

# Category Icons
LIVE_ICON = 'live.png'
LATEST_ICON = 'latest.png'
SCIENCE_ICON = 'science.png'
REVIEW_ICON = 'review.png'
APP_OF_THE_DAY_ICON = 'app-of-the-day.png'
DIY_ICON = 'diy.png'
COFFEE_ICON = 'coffee.png'
HOWTO_ICON = 'howto.png'
MAKERBOT_ICON = 'makerbot.png'
SEARCH_ICON = 'search.png'

# Creates the main menu (the first menu that pops up when opening the app)
@handler('/video/tested', 'Tested')
def MainMenu():
    oc = ObjectContainer()

    # Checks to see if a livestream is going on, since the Tested API is no longer around it checks the Justin TV API
    # Assumes live streams are on the "tested" channel
    LIVE_CHANNEL = 'tested'
    response = JSON.ObjectFromURL('http://api.justin.tv/api/stream/list.json?channel=' + LIVE_CHANNEL)

    if( len(response) > 0):
    
        stream = response[0] #This should be fine as there can only ever be one live stream going per channel
        
        url = 'http://www.justin.tv/widgets/live_embed_player.swf?channel=' + LIVE_CHANNEL + '&auto_play=true&start_volume=25'
        title = stream['title']
        
        oc.add(
            VideoClipObject(
                key=WebVideoURL(url),
                title='LIVE: ' + title,
                source_title='Justin.tv',
                thumb=R(LIVE_ICON),
                art=R(ART),
                rating_key=LIVE_CHANNEL
            )
        )

        
    oc.add(
        DirectoryObject(
            key='/video/tested/videos',
            title='Latest',
            summary='',
            thumb=R(LATEST_ICON),
            art=R(ART)
        )
    )
    
    # The categories were chosen using a script to see what the most popular tags were on tested youtube videos
    # Script can be found here: https://gist.github.com/2940575
    categories =    [ 
                        ('Science & Technology', 'Tech', '', R(SCIENCE_ICON)),
                        ('Reviews', 'review', '', R(REVIEW_ICON)),
                        ('App Of The Day', 'app,of,the,day', '', R(APP_OF_THE_DAY_ICON)),
                        ('DIY', 'diy', '', R(DIY_ICON)),
                        ('Coffee', 'coffee', '', R(COFFEE_ICON)),
                        ('Howtos', 'howto', '', R(HOWTO_ICON)),
                        ('Makerbot', 'makerbot', '', R(MAKERBOT_ICON))
                    ]
    for cat in categories:
        oc.add(
            DirectoryObject(
                key='/video/tested/videos/?cat_id=' + str(cat[1]),
                title=cat[0],
                summary='',
                thumb=cat[3],
                art=R(ART)
            )
        )

    oc.add(
        InputDirectoryObject(
            key=Callback(Videos),
            title='Search',
            prompt='Search',
            thumb=R(SEARCH_ICON),
            art=R(ART)
        )
    )

    return oc
    
# Handles when a category is selected from the main menu
@route('/video/tested/videos')
def Videos(cat_id=None, query=None, page = 1):

    # Apparently plex *always* passes parameters to these functions as strings
    # So have to 'unconvert' the parameters
    page = int(page)

    if query == '':
        query = None
        
    if cat_id == '':
        cat_id = None

    # Change this to change how many results are displayed per page, maximum is 50 according to youtube API
    MAXRESULTS = 20

    oc = ObjectContainer()

    Log(str(page))
    url_suffix = '&start-index=' + str((page - 1) * MAXRESULTS + 1)
    url_suffix += '&max-results=' + str(MAXRESULTS)
    
    if query:
        videos = JSON.ObjectFromURL('http://gdata.youtube.com/feeds/api/videos?alt=json&author=testedcom&prettyprint=true&v=2' + url_suffix + '&q=' + query.replace(' ', '%20'))
    elif cat_id:
        videos = JSON.ObjectFromURL('http://gdata.youtube.com/feeds/api/videos?alt=json&author=testedcom&prettyprint=true&v=2' + url_suffix + '&orderby=published&category=' + cat_id)
    else:
        videos = JSON.ObjectFromURL('https://gdata.youtube.com/feeds/api/users/testedcom/uploads?alt=json&prettyprint=true&v=2' + url_suffix )

  
    # The following tidbit was inspired by the youtube plugin that plex uses
    if videos['feed'].has_key('entry'):
    
        for video in videos['feed']['entry']:
        
            if CheckRejectedEntry(video):
                continue
                
            video_url = None
            for video_links in video['link']:
                if video_links['type'] == 'text/html':
                    video_url = video_links['href']
                    break
                
            if video_url is None:
                Log('Found video that had no URL')
                continue
                 
            video_title = video['media$group']['media$title']['$t']
            thumb = video['media$group']['media$thumbnail'][2]['url']
            duration = int(video['media$group']['yt$duration']['seconds']) * 1000  

            summary = None
            try: summary = video['media$group']['media$description']['$t']
            except: pass 

            rating = None
            try: rating = float(video['gd$rating']['average']) * 2
            except: pass

            date = None
            try: date = Datetime.ParseDate(video['published']['$t'].split('T')[0])
            except:
                try: date = Datetime.ParseDate(video['updated']['$t'].split('T')[0])
                except: pass
                
            oc.add(
                    VideoClipObject(
                        url=video_url + "&hd=1",
                        title=video_title,
                        summary=summary,
                        thumb=Callback(GetThumb, url = thumb),
                        art=R(ART),
                        rating = rating,
                        originally_available_at = date
                    )
            )
        
        # Handles pagination if there are more results that were not shown
        if videos['feed'].has_key('openSearch$totalResults'):
            total_results = int(videos['feed']['openSearch$totalResults']['$t'])
            items_per_page = int(videos['feed']['openSearch$itemsPerPage']['$t'])
            start_index = int(videos['feed']['openSearch$startIndex']['$t'])
            
            if not query:
                query = ''
               
            if not cat_id:
                cat_id = ''
            
            if (start_index + items_per_page) < total_results:
                oc.add(DirectoryObject(key = Callback(Videos, cat_id = cat_id, query = query, page = page + 1), title = 'Next'))

    return oc

# Retrives the thumbnail of a video from the given url, caching it
def GetThumb(url):
    try:
        data = HTTP.Request(url, cacheTime = CACHE_1WEEK).content
        return DataObject(data, 'image/jpeg')
    except:
        Log.Exception("Error when attempting to get the associated thumb")
        return Redirect(R(ICON))
        
# Checks to see if the video passed is a valid video (not deleted, rejected, restricted, etc
def CheckRejectedEntry(entry):
    try:
        status_name = entry['app$control']['yt$state']['name']

        if status_name in ['deleted', 'rejected', 'failed']:
            return True

        if status_name == 'restricted':
            status_reason = entry['app$control']['yt$state']['reasonCode']

            if status_reason in ['private', 'requesterRegion']:
                return True

    except:
        pass

    return False