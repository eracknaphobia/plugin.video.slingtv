# You should have received a copy of the GNU General Public License
# along with Sling.TV.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

from resources.lib.classes.auth import Auth
from resources.lib.globals import *


class Sling(object):

    def __init__(self, sysARG):
        global HANDLE_ID

        log('__init__')
        self.sysARG = sysARG
        HANDLE_ID = int(self.sysARG[1])
        log('Handle ID => %i' % HANDLE_ID)
        self.endPoints = self.buildEndPoints()
        self.handleID = int(self.sysARG[1])
        self.mode = None
        self.url = None
        self.params = None
        self.name = None
        self.auth = Auth()

        self.getParams()

    def run(self):
        if self.mode == "logout":
            log("logging_out")
            self.auth.logOut()
        else:
            global USER_SUBS, HANDLE_ID
            log(f'Addon {ADDON_NAME} entry...')
            loggedIn, message = self.auth.logIn(self.endPoints, USER_EMAIL, USER_PASSWORD)
            log(f"Sling Class is logIn() ==> Success: {loggedIn} Message: {message}")
            if message != "Already logged in.":
                notificationDialog(message)
            if loggedIn:
                gotSubs, message = self.auth.getUserSubscriptions()
                self.auth.getAccessJWT(self.endPoints)
                if gotSubs:
                    USER_SUBS = message
                log("self.user Subscription Attempt, Success => " + str(gotSubs) + " Message => " + message)
            else:
                sys.exit()

        if self.mode is None:
            self.buildMenu()
        elif self.mode == "ondemand":
            if self.url is not None:
                self.onDemand(self.url)
            else:
                self.onDemandCategories()
        elif self.mode == "play":
            self.play()
        elif self.mode == "settings":
            xbmcaddon.Addon().openSettings()

        xbmcplugin.setContent(int(self.sysARG[1]), CONTENT_TYPE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(self.sysARG[1]), xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]), xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(int(self.sysARG[1]), xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(int(self.sysARG[1]), updateListing=UPDATE_LISTING, cacheToDisc=False)

        xbmc.executebuiltin('Container.SetSortMethod(1)')

    def getParams(self):
        log('Retrieving parameters')

        self.params = dict(urlParse.parse_qsl(self.sysARG[2][1:]))
        if 'category' in self.params:
            self.params['category'] = binascii.unhexlify(self.params['category']).decode()
        try: self.url = urlLib.unquote(self.params['url'])
        except: pass
        try: self.name = urlLib.unquote_plus(self.params['name'])
        except: pass
        try: self.mode = self.params['mode']
        except: pass

        log(f'\rName: {self.name} | Mode: {self.mode}\rURL: {self.sysARG[0]}{self.sysARG[2]}\rParams:\r{self.params}')

    def buildMenu(self):
        log('Building Menu')        

        if self.mode is None:
            addDir("On Demand", self.handleID, '', "ondemand")
            addOption("Settings", self.handleID, '', mode='settings')

    def onDemandCategories(self):        
        od_headers = {            
            "Authorization": f"Bearer {SETTINGS.getSetting('access_token_jwt')}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "dma": USER_DMA,
            "timezone": USER_OFFSET,
            "geo-zipcode": USER_ZIP,
            "features": "use_ui_4=true,inplace_reno_invalidation=true,gzip_response=true,enable_extended_expiry=true,enable_home_channels=true,enable_iap=true,enable_trash_franchise_iview=false,browse-by-service-ribbon=true,subpack-hub-view=true,entitled_streaming_hub=false,add-premium-channels=false,enable_home_sports_scores=true,enable-basepack-ribbon=true,is_rewards_enabled=false",        
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "CLIENT-CONFIG": "rn-client-config",
            "Client-Version": "6.2.4",
            "Player-Version": "8.10.1",
            "Client-Analytics-ID": "",            
            "Device-Model": "Chrome",                        
            "page_size": "large",            
            "response-config": "ar_browser_1_1",            
            "Content-Type": "application/json; charset=UTF-8",
            "Origin": "https://watch.sling.com",
            "Connection": "keep-alive",
            "Referer": "https://watch.sling.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "TE": "trailers"
        }

        url = "https://p-cmwnext-fast.movetv.com/pres/on_demand_all"

        r = requests.get(url, headers=od_headers)    

        if r.ok:
            for ribbon in r.json()['ribbons']:
                if "title" in ribbon:
                    addDir(ribbon['title'], self.handleID, ribbon['href'], "ondemand")

    def onDemand(self, url):
        od_headers = {            
            "Authorization": f"Bearer {SETTINGS.getSetting('access_token_jwt')}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "dma": USER_DMA,
            "timezone": USER_OFFSET,
            "geo-zipcode": USER_ZIP,
            "features": "use_ui_4=true,inplace_reno_invalidation=true,gzip_response=true,enable_extended_expiry=true,enable_home_channels=true,enable_iap=true,enable_trash_franchise_iview=false,browse-by-service-ribbon=true,subpack-hub-view=true,entitled_streaming_hub=false,add-premium-channels=false,enable_home_sports_scores=true,enable-basepack-ribbon=true,is_rewards_enabled=false",        
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "CLIENT-CONFIG": "rn-client-config",
            "Client-Version": "6.2.4",
            "Player-Version": "8.10.1",
            "Client-Analytics-ID": "",            
            "Device-Model": "Chrome",                        
            "page_size": "large",            
            "response-config": "ar_browser_1_1",            
            "Content-Type": "application/json; charset=UTF-8",
            "Origin": "https://watch.sling.com",
            "Connection": "keep-alive",
            "Referer": "https://watch.sling.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "TE": "trailers"
        }
        r = requests.get(url, headers=od_headers)    

        if r.ok:
            for tile in r.json()['tiles']:
                if "title" in tile:
                    try:
                        name = tile["title"]
                        stream_url = tile["actions"]["PLAY_CONTENT"]["playback_info"]["url"]
                        icon = tile["image"]["url"]
                        addLink(name, self.handleID,  stream_url, "play", info=None, art=icon)
                    except:
                        pass

    def play(self):
        url = self.url
        name = self.name
        log(f'Playing stream {name}')
        #try:
        url, license_key, external_id, nba_channel = self.auth.getPlaylist(url, self.endPoints)
        # except:
        #     license_key = ''
        #     external_id = ''
        #     nba_channel = False
        
        log(f'{url} | {license_key} | {external_id}')
        liz = xbmcgui.ListItem(name, path=url)
        
        protocol = 'mpd'
        drm = 'com.widevine.alpha'
        mime_type = 'application/dash+xml'

        if protocol in url:
            is_helper = inputstreamhelper.Helper(protocol, drm=drm)

            if not is_helper.check_inputstream():
                sys.exit()

            liz.setProperty('inputstream', is_helper.inputstream_addon)
            liz.setProperty('inputstream.adaptive.manifest_type', protocol)
            liz.setProperty('inputstream.adaptive.stream_headers', 'User-Agent=' + USER_AGENT)
            liz.setProperty('inputstream.adaptive.manifest_headers', 'User-Agent=' + USER_AGENT)
            
            if license_key != '':
                liz.setProperty('inputstream.adaptive.license_type', drm)
                liz.setProperty('inputstream.adaptive.license_key', license_key)
            liz.setMimeType(mime_type)

            liz.setContentLookup(False)

            # if nba_channel:
            #     liz.setProperty('ResumeTime', '43200')
            #     liz.setProperty('TotalTime', '1')

        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)

        while not xbmc.Player().isPlayingVideo():
            xbmc.Monitor().waitForAbort(0.25)

        if external_id != '':
            play_back_started = time.time()
            while xbmc.Player().isPlayingVideo() and not xbmc.Monitor().abortRequested():
                position = int(float(xbmc.Player().getTime()))
                duration = int(float(xbmc.Player().getTotalTime()))
                xbmc.Monitor().waitForAbort(3)

            if int(time.time() - play_back_started) > 45:
                self.setResume(external_id, position, duration)

    def setResume(self, external_id, position, duration):
        # If there's only 2 min left delete the resume point
        if duration - position < 120:
            url = f"{self.endPoints['cmwnext_url']}/resumes/v4/resumes/{external_id}"
            payload = {
                    "platform": "browser",
                    "product": "sling"
            }
            requests.delete(url, headers=HEADERS, json=payload, auth=self.auth.getAuth(), verify=VERIFY)
        else:
            url = f"{self.endPoints['cmwnext_url']}/resumes/v4/resumes"
            payload = {
                    "external_id": external_id,
                    "position": position,
                    "duration": duration,
                    "resume_type": "fod",
                    "platform": "browser",
                    "product": "sling"
            }

            requests.put(url, headers=HEADERS, json=payload, auth=self.auth.getAuth(), verify=VERIFY)

    def buildEndPoints(self):
        log(f'Building endPoints\r{WEB_ENDPOINTS}')
        endpoints = {}
        response = requests.get(WEB_ENDPOINTS, headers=HEADERS, verify=VERIFY)
        if response.ok:
            endpoints = response.json()['environments']['production']

        return endpoints



