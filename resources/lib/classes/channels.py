from resources.lib.globals import *


class CHANNELS:
    cms_url = ''
    channels_url = ''
    channels = []

    def __init__(self):

        env_urls = get_env_url()
        self.cms_url = env_urls['cms_url']
        self.channels_url = env_urls['channels_url']
        self.get_channels()

    def get_channels(self):
        if USER_OFFSET == '' or USER_DMA == '':
            log("User has not logged in")
            return self.channels
        debug = dict(urlParse.parse_qsl(DEBUG_CODE))
        if 'channels' in debug:
            channels_url = self.channels_url
            r = requests.get(channels_url, headers=HEADERS)
            self.build_channels(r.json()['channels'])
        else:
            subs = binascii.b2a_base64(str.encode(LEGACY_SUBS.replace('+', ','))).decode().strip()
            channels_url = f"{self.cms_url}/cms/publish3/domain/channels/v4/{USER_OFFSET}/{USER_DMA}/{subs}/1.json"
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

        if self.channels:
            self.channels = sorted(self.channels, key=lambda x: x['name'].upper().split('THE ')[1] if 'THE ' in x['name'].upper() else x['name'].upper())
        return self.channels

    def build_channels(self, channels):
        for channel in channels:
            if 'metadata' in channel:
                if xbmc.Monitor().abortRequested():
                    break
                # Make language a optional setting
                language = channel['metadata']['language'].lower() if 'language' in channel['metadata'] else ''
                linear_channel = channel['metadata']['is_linear_channel'] if 'is_linear_channel' in channel[
                    'metadata'] else False
                sling_free = True if 'genre' in channel['metadata'] and 'Sling Free' in channel['metadata'][
                    'genre'] else False
                
                if (linear_channel and language == 'english' and not any(d['name'] == channel['metadata']['channel_name'] for d in self.channels)
                        and (sling_free or CHANNELS)):
                    channel_dict = {
                        'name': channel['metadata']['channel_name'],
                        'stream': f'plugin://plugin.video.slingtv/?mode=play&url={channel["qvt_url"]}',
                        'id': channel['title'],
                        'logo': channel['thumbnail']['url'],
                        'preset': channel['channel_number'],
                        'group': channel['metadata']['genre'] if 'genre' in channel['metadata'] else []
                    }
                    self.channels.append(channel_dict)
