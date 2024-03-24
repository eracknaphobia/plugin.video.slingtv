from resources.lib.globals import *
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class EPG:
    channels = []

    def __init__(self):
        env_urls = get_env_url()
        self.cms_url = env_urls['cms_url']
        self.channels_url = env_urls['channels_url']
        self.monitor = xbmc.Monitor()

    def get_channels(self):
        debug = dict(urlParse.parse_qsl(DEBUG_CODE))
        if 'channels' in debug:
            channels_url = self.channels_url
            r = requests.get(channels_url, headers=HEADERS)
            self.build_channels(r.json()['channels'])
            return

        subs = binascii.b2a_base64(str.encode(LEGACY_SUBS.replace('+', ','))).decode().strip()
        if subs:
            channels_url = f"{self.cms_url}/cms/publish3/domain/channels/v4/{USER_OFFSET}/{USER_DMA}/{subs}/1.json"
        else:
            channels_url = f"{self.cms_url}/cms/publish3/domain/channels/v4/{USER_OFFSET}/{USER_DMA}/MTUw/1.json"
        response = requests.get(channels_url, headers=HEADERS)
        if response.ok:
            response = response.json()
            if 'subscriptionpacks' in response:
                sub_packs = response['subscriptionpacks']
                for sub_pack in sub_packs:
                    if sub_pack['title'].lower() == "freestream" and FREE_STREAMS == 'false':
                        continue
                    if 'channels' in sub_pack:
                        self.build_channels(sub_pack['channels'])

    def build_channels(self, channels):
        for channel in channels:
            if 'metadata' in channel:
                if self.monitor.abortRequested():
                    break
                # Make language a optional setting
                language = channel['metadata']['language'].lower() if 'language' in channel['metadata'] else ''
                linear_channel = channel['metadata']['is_linear_channel'] if 'is_linear_channel' in channel[
                    'metadata'] else False
                sling_free = True if 'genre' in channel['metadata'] and 'Sling Free' in channel['metadata'][
                    'genre'] else False

                if linear_channel and language == 'english' and (sling_free or FREE_ACCOUNT == 'false'):
                    genre = ''
                    try:
                        genre = str(channel['metadata']['genre'][0])
                    except:
                        pass
                    self.channels.append(
                        (channel['channel_guid'],
                         channel['title'],
                         channel['metadata']['channel_name'],
                         channel['thumbnail']['url'],
                         channel['qvt_url'],
                         genre)
                    )

        if self.channels:
            self.channels = sorted(self.channels,
                                   key=lambda x: x[1].upper().split('THE ')[1] if 'THE ' in x[1].upper() else
                                   x[1].upper())

    def get_epg_data(self):
        from collections import defaultdict
        epg = defaultdict(list)

        if USER_OFFSET == '' or USER_DMA == '':
            log("User has not logged in")
            return epg

        self.get_channels()

        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        progress = xbmcgui.DialogProgressBG()
        progress.create("Sling TV", "Getting EPG Info...")
        for day in range(0, 1):
            i = 0
            for channel in self.channels:
                if self.monitor.abortRequested():
                    break
                url_timestamp = (datetime.date.today() + datetime.timedelta(days=day)).strftime(
                    "%y%m%d") + datetime.datetime.utcnow().strftime("%H%M")
                schedule_url = f"{self.cms_url}/cms/publish3/channel/schedule/24/{url_timestamp}/1/{channel[0]}.json"
                xbmc.log(f"{channel[2]}")
                xbmc.log(schedule_url)
                i += 1
                progress.update(int((i / len(self.channels)) * 100), message=f"{channel[2]}")
                
                try:
                    r = session.get(schedule_url, headers=HEADERS, timeout=10)
                except:
                    pass

                if not r.ok or 'schedule' not in r.json() or 'scheduleList' not in r.json()['schedule']: continue
                channel_id = channel[1]
                stream_url = channel[4]
                # try:
                for slot in r.json()['schedule']['scheduleList']:
                    epg_dict = {}
                    start_time = datetime.datetime.utcfromtimestamp(
                        int(str(slot['schedule_start']).replace('.000', ''))).strftime('%Y-%m-%dT%H:%M:%S')
                    stop_time = datetime.datetime.utcfromtimestamp(
                        int(str(slot['schedule_stop']).replace('.000', ''))).strftime('%Y-%m-%dT%H:%M:%S')
                    title = str(slot['title'])
                    sub_title = slot['metadata']['episode_title'] if 'episode_title' in slot['metadata'] else ''
                    desc = slot['metadata']['description'] if 'description' in slot['metadata'] else ''
                    xbmc.log(title)
                    image = ''
                    if 'thumbnail' in slot and slot['thumbnail']:
                        image = slot['thumbnail']['url']
                    elif 'program' in slot and slot['program']['franchise_image'] is not None:
                        image = slot['program']['franchise_image']
                    air_date = slot['orig_air_date'] if 'orig_air_date' in slot else ''
                    genres = ''
                    if 'genre' in slot['metadata']:
                        for genre in slot['metadata']['genre']:
                            genres += f"{genre} "

                    epg_dict['start'] = start_time
                    epg_dict['stop'] = stop_time
                    epg_dict['title'] = title
                    epg_dict['description'] = desc
                    epg_dict['subtitle'] = sub_title
                    epg_dict['stream'] = stream_url
                    epg_dict['image'] = image
                    epg_dict['date'] = air_date
                    epg_dict['genre'] = genres

                    if 'episode_season' in slot['metadata'] and 'episode_number' in slot['metadata']:
                        s = slot['metadata']['episode_season']
                        e = slot['metadata']['episode_number']
                        if s != 0 and e != 0:
                            episode = f'S{s}E{e}'
                            epg_dict['episode'] = episode

                    epg[channel_id].append(epg_dict)

            progress.close()
            return epg
