from resources.lib.globals import *
from requests_oauthlib import OAuth1
import uuid


class Auth(object):
    global BASE_API

    HASH = '441e030d03595a122a281d081b1608511804776b42634b444443456a466b1c444d5b4f431e7860760263404f67445c617c7b46167' \
           '96767691d5a1d595d786445451f411e59697e627f7a181b657b484f6f020202'
    OTL_URL = '%s/v5/sessions?client_application=ottweb&format=json&locale=en' % BASE_API
    OTK_URL = '%s/v5/users/access_from_jwt' % BASE_API
    ACCESS_TOKEN = ''
    ACCESS = SETTINGS.getSetting('access')
    OCK = ''
    OCS = ''
    OTL = ''
    OTK = ''
    OTS = ''

    def __init__(self):
        log('auth::init()')
        self.deviceID()
        if self.ACCESS == '':
            self.ACCESS = self.HASH
        self.getAccess()

    def deviceID(self):
        global DEVICE_ID
        log('auth::deviceID()')
        if DEVICE_ID == '':
            DEVICE_ID = str(uuid.uuid4())
            SETTINGS.setSetting('device_id', DEVICE_ID)
            log('auth::deviceID() New ID %s' % DEVICE_ID)

    def loggedIn(self):
        log('auth:loggedIn()')
        if self.OTK == '' or self.OTS == '':
            log('auth:loggedIn() No auth token')
            return False, 'OAuth access is blank, not logged in.', {}

        auth = OAuth1(self.OCK, self.OCS, self.OTK, self.OTS)
        user_headers = HEADERS
        user_headers.pop('Content-Type', None)
        r = requests.get(USER_INFO_URL, headers=user_headers, auth=auth, verify=VERIFY)
        log(f"{r.text}")
        if r.ok:
            response_json = r.json()
            if 'email' in response_json:
                if response_json['email'] == USER_EMAIL:
                    log('auth::loggedIn() Account Active')
                    return True, 'Account email matches USER_EMAIL, logged in.', response_json
                else:
                    log('auth::loggedIn() Account Mismatch')
                    SETTINGS.setSetting('access', '')
                    SETTINGS.setSetting('user_email', '')
                    SETTINGS.setSetting('password', '')
                    return False, 'Account email does not match USER_EMAIL, not logged in.', {}
            else:
                log('auth::loggedIn() Account info not retrieved')
                SETTINGS.setSetting('access', '')
                SETTINGS.setSetting('user_email', '')
                SETTINGS.setSetting('password', '')
                return False, 'Account info corrupt, not logged in.', {}
        else:
            log('auth::loggedIn() Access Denied')
            SETTINGS.setSetting('access', '')
            return False, 'Account info access denied', {}

    def getRegionInfo(self):
        global USER_DMA, USER_OFFSET, USER_ZIP
        log('auth::getRegionInfo()')
        if not self.loggedIn(): return False, 'Must be logged in to retrieve region info.'
        log('auth::getRegionInfo()  Subscriber ID: %s  | Device ID: %s' % (SUBSCRIBER_ID, DEVICE_ID))
        if SUBSCRIBER_ID == '': return False, 'SUBSCRIBER_ID and DEVICE_ID required for getRegionInfo()'
        if DEVICE_ID == '':
            self.deviceID()
        regionUrl = BASE_GEO.format(SUBSCRIBER_ID, DEVICE_ID)
        headers = {
            "Host": "p-geo.movetv.com",
            "Connection": "keep-alive",
            "Origin": "https://watch.sling.com",
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Referer": "https://watch.sling.com/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9"
        }
        r = requests.get(regionUrl, headers=headers, verify=VERIFY)
        temp_response = r.json()
        if r.ok:
            if 'lookup_address' in temp_response:
                temp_response['lookup_address'] = '***REDACTED***'
            if 'city' in temp_response:
                temp_response['city'] = '***REDACTED***'
            if 'state' in temp_response:
                temp_response['state'] = '***REDACTED***'
            if 'zip_code' in temp_response:
                temp_response['zip_code'] = '***REDACTED***'
            if 'country' in temp_response:
                temp_response['country'] = '***REDACTED***'
            if 'latitude' in temp_response:
                temp_response['latitude'] = '***REDACTED***'
            if 'longitude' in temp_response:
                temp_response['longitude'] = '***REDACTED***'
            
            log("auth::getRegionInfo() Response => %s" % json.dumps(temp_response, indent=4))
        if r.ok:
            USER_DMA = str(r.json().get('dma', {}) or '')
            USER_OFFSET = (r.json().get('time_zone_offset', {}) or '')
            USER_ZIP = str(r.json().get('zip_code', {}) or '')

            debug = dict(urlParse.parse_qsl(DEBUG_CODE))
            if 'dma' in debug:
                USER_DMA = debug['dma']

            SETTINGS.setSetting('user_dma', USER_DMA)
            SETTINGS.setSetting('user_offset', USER_OFFSET)
            SETTINGS.setSetting('user_zip', USER_ZIP)
            return True, {"USER_DMA": USER_DMA, "USER_OFFSET": USER_OFFSET}
        else:
            return False, 'Failed to retrieve user region info.'

    def getUserSubscriptions(self):
        global SUBSCRIBER_ID
        log('auth::getUserSubscriptions()')
        loggedIn, message, json_data = self.loggedIn()
        if not loggedIn: return False, 'Must be logged in to retrieve subscriptions.'
        
        if json_data is not None:
            if 'postal_code' in json_data:
                json_data['postal_code'] = '***REDACTED***'
            if 'billing_zipcode' in json_data:
                json_data['billing_zipcode'] = '***REDACTED***'
            if 'email' in json_data:
                json_data['email'] = '***REDACTED***'
            if 'billing_method' in json_data:
                json_data['billing_method'] = '***REDACTED***'
            if 'name' in json_data:
                json_data['name'] = '***REDACTED***'

            log("auth::getUserSubscriptions() Response = > " + json.dumps(json_data, indent=4))
        
            subscriptions = json_data['subscriptionpacks']
            sub_packs = ''
            legacy_subs = ''
            for subscription in subscriptions:
                if sub_packs != '':
                    sub_packs += "+"
                sub_packs += subscription['guid']
                if legacy_subs != '':
                    legacy_subs += "+"
                legacy_subs += str(subscription['id'])

            debug = dict(urlParse.parse_qsl(DEBUG_CODE))
            log('Debug Code: %s' % json.dumps(debug, indent=4))
            if 'user_subs' in debug:
                sub_packs = debug['user_subs'].replace(',', '+')
            if 'legacy_subs' in debug:
                legacy_subs = debug['legacy_subs']

            SETTINGS.setSetting('user_subs', sub_packs)
            SETTINGS.setSetting('legacy_subs', legacy_subs)

            return True, sub_packs

    def getAuth(self):
        return OAuth1(self.OCK, self.OCS, self.OTK, self.OTS)

    def getOTK(self, endPoints):
        log('auth::getOTK()')
        self.deviceID()
        self.getAccess()

        # Validate account
        payload = f"email={requests.utils.quote(USER_EMAIL)}&password={requests.utils.quote(USER_PASSWORD)}&device_guid={requests.utils.quote(DEVICE_ID)}"
        account_headers = HEADERS
        account_headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        account_headers['User-Agent'] = ANDROID_USER_AGENT
        auth = OAuth1(self.OCK, self.OCS)
        r = requests.put(f"{endPoints['ums_url']}/v3/xauth/access_token.json", headers=account_headers, data=payload, auth=auth, verify=VERIFY)

        if r.ok and 'oauth_token' in r.json():
            self.OTK = r.json()['oauth_token']
            self.OTS = r.json()['oauth_token_secret']
            self.OTL = 'NO-LONGER-IN-USE'
            log('auth::getOTK() Got OAuth tokens')

            self.setAccess()
            return True, 'Successfully retrieved user OAuth token. \r%s | %s' % (self.OTK, self.OTS)
        else:
            log('auth::getOTK() Failed to retrieve OAuth token')
            return False, 'Failed to retrieve user OAuth token %i' % r.status_code

    def paidLogin(self, endPoints):
        global USER_EMAIL, USER_PASSWORD
        email = inputDialog(LANGUAGE(30002))
        password = inputDialog(LANGUAGE(30003), opt=xbmcgui.ALPHANUM_HIDE_INPUT)
        SETTINGS.setSetting('User_Email', email)
        SETTINGS.setSetting('User_Password', password)
        USER_EMAIL = email
        USER_PASSWORD = password

        # Check if account exists
        payload = {
            'request_context': {
                'application_name': 'Browser',
                'interaction_id': 'Browser:%s' % DEVICE_ID[:7],
                'partner_name': 'Browser',
                'request_id': str(random.randint(0, 999)),
                'timestamp': str(time.mktime(datetime.datetime.utcnow().timetuple())).split('.')[0]
            },
            'request': {
                'email': USER_EMAIL
            }
        }
        auth = OAuth1(self.OCK, self.OCS)
        r = requests.post(f"{endPoints['extauth_url']}/user/lookup", headers=HEADERS, data=json.dumps(payload), auth=auth, verify=VERIFY)
        log(f"{r.text}")
        if r.ok:
            log('auth::logIn() =>\r%s' % json.dumps(r.json()['response_context'], indent=4))
            if 'response' in r.json():
                account = r.json()['response']
                if 'guid' in account:
                    SUBSCRIBER_ID = account['guid']
                    SETTINGS.setSetting('subscriber_id', SUBSCRIBER_ID)
                    if self.OTK == '':
                        gotOTK, message = self.getOTK(endPoints)
                        if gotOTK:
                            SETTINGS.setSetting('free_account', 'false')
                            return True, 'Successfully logged in.'
                        else:
                            self.logOut()
                            return False, "Failed to log in, check credentials"
                    else:
                        return True, 'Successfully logged in.'
                else:
                    self.logOut()
                    return False, 'Account is not active'
            else:
                self.logOut()
                return False, 'Failed to validate account'
        else:
            self.logOut()
            return False, 'Unable to validate account'

    def prospectLogin(self, endPoints):
        global SUBSCRIBER_ID, USER_EMAIL
        log('auth::prospectLogin()')
        self.deviceID()
        self.getAccess()

        payload = {"deviceGuid": DEVICE_ID}
        account_headers = HEADERS
        account_headers['Content-Type'] = 'application/json; charset=UTF-8'
        account_headers['User-Agent'] = ANDROID_USER_AGENT
        auth = OAuth1(self.OCK, self.OCS)
        r = requests.post(f"{endPoints['extauth_url']}/user/prospect",
                                 headers=account_headers, json=payload, auth=auth, verify=VERIFY)

        log(f"{r.json()}")
        if r.ok and 'statusMessage' in r.json() and r.json()['statusMessage'].lower() == 'successful':
            user_info = r.json()['response']['userInfo']
            self.OTK = user_info['accessToken']
            self.OTS = user_info['accessSecret']
            self.OTL = 'NO-LONGER-IN-USE'
            log('auth::getOTK() Got OAuth tokens')
            SUBSCRIBER_ID = user_info['userGuid']
            SETTINGS.setSetting('subscriber_id', SUBSCRIBER_ID)

            self.setAccess()
            # Set Prospect Email
            auth = OAuth1(self.OCK, self.OCS, self.OTK, self.OTS)
            user_headers = HEADERS
            user_headers.pop('Content-Type', None)
            r = requests.get(USER_INFO_URL, headers=user_headers, auth=auth, verify=VERIFY)
            if r.ok:
                USER_EMAIL = r.json()["email"]
                SETTINGS.setSetting('User_Email', USER_EMAIL)
                SETTINGS.setSetting('free_account', 'true')
            return True, 'Free Account Created successfully'
        else:
            log('auth::getOTK() Failed to retrieve OAuth token')
            return False, 'Failed to retrieve user OAuth token %i' % r.status_code

    def logIn(self, endPoints, email=USER_EMAIL, password=USER_PASSWORD):
        result = False
        msg = "Not logged in."
        # Check if already logged in
        status, message, json_data = self.loggedIn()
        log("auth::logIn() => Already loggedIn() %r, %s" % (status, message))
        if status:
            return status, 'Already logged in.'

        # First launch, credentials empty
        if email == '' or password == '':
            # firstrun wizard
            answer = yesNoCustomDialog(LANGUAGE(30006), custom="Stream Free", no=LANGUAGE(30004), yes=LANGUAGE(30005))
            if answer == 1:
                result, msg = self.paidLogin(endPoints)
            elif answer == 2:
                #Free Stream
                result, msg = self.prospectLogin(endPoints)
            else:
                result = False
                msg = 'Login Aborted'

        return result, msg

    def logOut(self):
        SETTINGS.setSetting('access_token', '')
        SETTINGS.setSetting('User_Email', '')
        SETTINGS.setSetting('User_Password', '')
        SETTINGS.setSetting('subscriber_id', '')
        SETTINGS.setSetting('user_dma', '')
        SETTINGS.setSetting('user_subs', '')
        SETTINGS.setSetting('legacy_subs', '')

    def xor(self, data, key):
        return ''.join(chr(ord(s) ^ ord(c)) for s, c in zip(data, key * 100))

    def getAccess(self):
        global DEVICE_ID, ADDON_ID
        if self.ACCESS == self.HASH:
            key = 'plugin.video.sling'.ljust(164, '.')
        else:
            key = DEVICE_ID.ljust(164, '.')
        decoded_access = self.xor(binascii.unhexlify(self.ACCESS).decode(), key)
        log(f"{decoded_access}")
        access_array = decoded_access.split(',')

        if len(access_array) < 5:
            return False
        else:
            self.OCK = access_array[0]
            self.OCS = access_array[1]
            self.OTL = access_array[2]
            self.OTK = access_array[3]
            self.OTS = access_array[4]
            self.getRegionInfo()
            return True

    def setAccess(self):
        global DEVICE_ID, ADDON_ID
        key = DEVICE_ID.ljust(164, '.')
        #payload = ('%s,%s,%s,%s,%s' % (self.OCK, self.OCS, self.OTL, self.OTK, self.OTS))
        payload = f'{self.OCK},{self.OCS},{self.OTL},{self.OTK},{self.OTS}'
        new_access = binascii.hexlify(str.encode(self.xor(payload, key)))
        SETTINGS.setSetting('access', new_access)
        self.ACCESS = new_access

    def getAccessJWT(self, endPoints):
        global ACCESS_TOKEN_JWT
        if ACCESS_TOKEN_JWT == '':
            payload = {'device_guid': DEVICE_ID, 'platform': 'browser', 'product': 'sling'}
            r = requests.post(f"{endPoints['cmwnext_url']}/cmw/v1/client/jwt", headers=HEADERS,
                                     data=json.dumps(payload), auth=self.getAuth())
            if r.ok and 'jwt' in r.json():
                ACCESS_TOKEN_JWT = r.json()['jwt']
                SETTINGS.setSetting('access_token_jwt', ACCESS_TOKEN_JWT)

    def getPlaylist(self, playlist_url, end_points):
        log('auth::getPlaylist() URL: %s' % playlist_url)
        license_key = ''
        nba_channel = False
        r = requests.get(playlist_url, headers=HEADERS, verify=VERIFY)
        log(r.text)
        if r.ok:
            qmx_url = None
            video = r.json()
            if video is None or 'message' in video: return
            if 'playback_info' not in video: sys.exit()
            mpd_url = video['playback_info']['dash_manifest_url']
            if 'ad_info' in video['playback_info'] \
                    and 'channel_name' in video['playback_info']['ad_info'] \
                    and video['playback_info']['ad_info']['channel_name'] == "nba_league_pass": nba_channel = True
            for clip in video['playback_info']['clips']:
                if clip['location'] != '' and clip['location'] is not None:
                    qmx_url = clip['location']
                    break
            log(f"qmx_url:{qmx_url}")
            if 'UNKNOWN' not in mpd_url and qmx_url is not None:
                r = requests.get(qmx_url, headers=HEADERS, verify=VERIFY)
                log(r.text)
                if r.ok:
                    # START: CDN Server error temporary fix
                    message = 'Sorry, our service is currently not available in your region'
                    if message in r.text:
                        qmx_url = re.sub(r"p-cdn\d", "p-cdn1", qmx_url)
                        r = requests.get(qmx_url, headers=HEADERS, verify=VERIFY)
                        mpd_url = re.sub(r"p-cdn\d", "p-cdn1", mpd_url)
                    # END: CDN Server error temporary fix

                    qmx = r.json()
                    if 'message' in qmx: return
                    lic_url = ''
                    if 'encryption' in qmx:
                        lic_url = qmx['encryption']['providers']['widevine']['proxy_url']
                        log('resolverURL, lic_url = ' + lic_url)

                    if 'playback_info' in playlist_url:
                        channel_id = playlist_url.split('/')[-4]
                    else:
                        channel_id = playlist_url.split('/')[-2]
                        if 'channel=' in playlist_url:
                            channel_id = playlist_url.split('?')[-1].split('=')[-1]                        

                    debug = dict(urlParse.parse_qsl(DEBUG_CODE))
                    if 'channel' in debug:
                        channel_id = debug['channel']
                    if lic_url != '':
                        license_key = '%s|User-Agent=%s|{"env":"production","user_id":"%s","channel_id":"%s","message":[D{SSM}]}|' % (
                            lic_url, ANDROID_USER_AGENT, SUBSCRIBER_ID, channel_id)

                    log('auth::getPlaylist() license_key: %s' % license_key)
            else:
                if 'linear_info' in video['playback_info']:
                    if 'disney_stream_service_url' in video['playback_info']['linear_info']:
                        mpd_url = self.get_disney_stream(end_points, video)
                    elif 'pluto.tv' in video['playback_info']['linear_info']['media_url']:
                        mpd_url = self.get_pluto_stream(video)
                    else:
                        mpd_url = self.get_drm_free_stream(video)

                elif 'vod_info' in video['playback_info']:
                    fod_url = video['playback_info']['vod_info'].get('media_url', '')
                    r = requests.get(fod_url, headers=HEADERS, verify=VERIFY)
                    if r.ok:
                        mpd_url = r.json()['stream']
                    elif 'message' in r.json():
                        notificationDialog(r.json()['message'])

            asset_id = ''
            if 'entitlement' in video and 'asset_id' in video['entitlement']:
                asset_id = video['entitlement']['asset_id']
            elif 'playback_info' in video and 'asset' in video['playback_info'] and 'guid' in \
                    video['playback_info']['asset']:
                asset_id = video['playback_info']['asset']['guid']

            return mpd_url, license_key, asset_id, nba_channel

    def get_disney_stream(self, end_points, video):
        mpd_url = ''
        log('auth::getPlaylist() Inside Disney/ABC')
        utc_datetime = str(time.mktime(datetime.datetime.utcnow().timetuple())).split('.')[0]
        sha1_user_id = hashlib.sha1(SUBSCRIBER_ID.encode()).hexdigest()
        rsa_sign_url = f"{end_points['cmwnext_url']}/cmw/v1/rsa/sign"
        stream_headers = HEADERS
        stream_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        payload = f'document={sha1_user_id}_{utc_datetime}_'
        log(f'getPlaylist, RSA payload => {payload}')
        r = requests.post(rsa_sign_url, headers=stream_headers, data=payload, verify=VERIFY)
        if r.ok and 'signature' in r.json():
            signature = r.json()['signature']
            log('auth::getPlaylist() RSA Signature: %s' % signature)
            disney_info = video['playback_info']['linear_info']
            if 'abc' in disney_info['disney_network_code']:
                brand = '003'
            else:
                brand = disney_info['disney_brand_code']
            params = {
                'ak': 'fveequ3ecb9n7abp66euyc48',
                'brand': brand,
                'device': '001_14',
                'locale': disney_info.get('disney_locale', ''),
                'token': f'{sha1_user_id}_{utc_datetime}_{signature}',
                'token_type': 'offsite_dish_ott',
                'user_id': sha1_user_id,
                'video_type': 'live',
                'zip_code': USER_ZIP
            }
            service_url = disney_info['disney_stream_service_url']
            payload = ''
            for key in params.keys():
                payload += f'{key}={params[key]}&'
            payload = payload[:-1]
            r = requests.post(service_url, headers=stream_headers, data=payload, verify=VERIFY)
            log(f"auth::getPlaylist() Disney response code: {r.status_code}")
            if r.ok:
                log(str(r.text))
                session_xml = xmltodict.parse(r.text)
                service_stream = session_xml['playmanifest']['channel']['assets']['asset']['#text']
                log(f'auth::getPlaylist() XML Stream: {service_stream}')
                mpd_url = service_stream

        return mpd_url

    def get_pluto_stream(self, video):
        media_url = video['playback_info']['linear_info'].get('media_url', '')
        parsed_url = urlLib.urlparse(media_url)
        params = urlLib.parse_qs(parsed_url.query)
        channel_id = params['channel'][0]
        hls_url = f"https://service-stitcher.clusters.pluto.tv/v1/stitch/embed/hls/channel/{channel_id}/master.m3u8?advertisingId=channel&appName=rokuchannel&appVersion=1.0&bmodel=bm1&channel_id=channel&content=channel&content_rating=ROKU_ADS_CONTENT_RATING&content_type=livefeed&coppa=false&deviceDNT=1&deviceId=channel&deviceMake=rokuChannel&deviceModel=web&deviceType=rokuChannel&deviceVersion=1.0&embedPartner=rokuChannel&genre=ROKU_ADS_CONTENT_GENRE&is_lat=1&platform=web&rdid=channel&studio_id=viacom&tags=ROKU_CONTENT_TAGS"
        
        return hls_url

    def get_drm_free_stream(self, video):
        mpd_url = ''
        media_url = video['playback_info']['linear_info'].get('media_url', '')
        log(f"media_url: {media_url}")
        r = requests.get(media_url, headers=HEADERS, verify=VERIFY)
        log(r.text)
        if r.ok:
            mpd_url = r.json()['manifest_url']
            log(f"manifest_url: {mpd_url}")
        elif 'message' in r.json():
            notificationDialog(r.json()['message'])

        return mpd_url