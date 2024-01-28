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
            addOption("Settings", self.handleID, '', mode='settings')

    def play(self):
        url = self.url
        name = self.name
        log(f'Playing stream {name}')
        try:
            url, license_key, external_id = self.auth.getPlaylist(url, self.endPoints)
        except:
            license_key = ''
            external_id = ''
        
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

            if license_key != '':
                liz.setProperty('inputstream.adaptive.license_type', drm)
                liz.setProperty('inputstream.adaptive.license_key', license_key)
            liz.setMimeType(mime_type)

            liz.setContentLookup(False)

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



