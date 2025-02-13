from .common import InfoExtractor
import re
import urllib.parse
from ..utils import (
    parse_iso8601,
    urlencode_postdata,
    mimetype2ext,
)


class BlackboardCollaborateIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        https?://
                        (?P<region>[a-z-]+)\.bbcollab\.com/
                        (?:
                            collab/ui/session/playback/load|
                            recording
                        )/
                        (?P<id>[^/\?]+)
                        \??(authToken=(?P<token>[\w\.\-]+))?'''
    _TESTS = [
        {
            'url': 'https://us-lti.bbcollab.com/collab/ui/session/playback/load/0a633b6a88824deb8c918f470b22b256',
            'md5': 'bb7a055682ee4f25fdb5838cdf014541',
            'info_dict': {
                'id': '0a633b6a88824deb8c918f470b22b256',
                'title': 'HESI A2 Information Session - Thursday, May 6, 2021 - recording_1',
                'ext': 'mp4',
                'duration': 1896,
                'timestamp': 1620333295,
                'upload_date': '20210506',
                'subtitles': {
                    'live_chat': 'mincount:1',
                },
            },
        },
        {
            'url': 'https://eu.bbcollab.com/collab/ui/session/playback/load/4bde2dee104f40289a10f8e554270600',
            'md5': '108db6a8f83dcb0c2a07793649581865',
            'info_dict': {
                'id': '4bde2dee104f40289a10f8e554270600',
                'title': 'Meeting - Azerbaycanca erize formasi',
                'ext': 'mp4',
                'duration': 880,
                'timestamp': 1671176868,
                'upload_date': '20221216',
            }
        },
        {
            'url': 'https://eu.bbcollab.com/recording/f83be390ecff46c0bf7dccb9dddcf5f6',
            'md5': 'e3b0b88ddf7847eae4b4c0e2d40b83a5',
            'info_dict': {
                'id': 'f83be390ecff46c0bf7dccb9dddcf5f6',
                'title': 'Keynote lecture by Laura Carvalho - recording_1',
                'ext': 'mp4',
                'duration': 5506,
                'timestamp': 1662721705,
                'upload_date': '20220909',
                'subtitles': {
                    'live_chat': 'mincount:1',
                },
            }
        },
        {
            'url': 'https://eu.bbcollab.com/recording/c3e1e7c9e83d4cd9981c93c74888d496',
            'md5': 'fdb2d8c43d66fbc0b0b74ef5e604eb1f',
            'info_dict': {
                'id': 'c3e1e7c9e83d4cd9981c93c74888d496',
                'title': 'International Ally User Group - recording_18',
                'ext': 'mp4',
                'duration': 3479,
                'timestamp': 1721919621,
                'upload_date': '20240725',
                'subtitles': {
                    'en': 'mincount:1',
                    'live_chat': 'mincount:1',
                },
            }
        },
        {
            'url': 'https://us.bbcollab.com/collab/ui/session/playback/load/76761522adfe4345a0dee6794bbcabda',
            'only_matching': True,
        },
        {
            'url': 'https://ca.bbcollab.com/collab/ui/session/playback/load/b6399dcb44df4f21b29ebe581e22479d',
            'only_matching': True,
        },
        {
            'url': 'https://eu.bbcollab.com/recording/51ed7b50810c4444a106e48cefb3e6b5',
            'only_matching': True,
        },
        {
            'url': 'https://au.bbcollab.com/collab/ui/session/playback/load/2bccf7165d7c419ab87afc1ec3f3bb15',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        # Prepare for requests
        mobj = self._match_valid_url(url)
        region = mobj.group('region')
        video_id = mobj.group('id')
        token = mobj.group('token')

        headers = {'Authorization': f'Bearer {token}'}
        base_url = f'https://{region}.bbcollab.com/collab/api/csa/recordings/{video_id}'

        # Try request the way the player handles it when behind a login
        video_info = (self._download_json(f'{base_url}/data/secure', video_id, 'Using auth token (if available)',
                                          headers=headers, fatal=False) or
        # Blackboard will allow redownloading from the same IP without authentication for a while, so if previous method fails, try this
               self._download_json(f'{base_url}/data', video_id, 'Trying fallback'))

        # Get metadata
        duration = video_info.get('duration')/1000
        title = video_info.get('name')
        upload_date = video_info.get('created')

        # Get streams
        stream_formats = []
        streams = video_info.get('extStreams')

        for i, current_stream in enumerate(streams):
            stream_formats.append({
                'url': current_stream['streamUrl'],
                'container': mimetype2ext(current_stream.get('contentType')),
                'aspect_ratio': video_info.get('aspectRatio', ''),
                })

        # Get subtitles
        subtitles = {}
        subs = video_info.get('subtitles')
        for current_subs in subs:
            lang_code = current_subs.get('lang')
            subtitles.setdefault(lang_code, []).append({
                'name': current_subs.get('label'),
                'url': current_subs['url']
                })

        # Get chat
        chats = video_info.get('chats')
        for current_chat in chats:
            subtitles.setdefault('live_chat', []).append({'url': current_chat['url']})

        return {
            'duration': duration,
            'formats': stream_formats,
            'id': video_id,
            'timestamp': parse_iso8601(upload_date),
            'subtitles': subtitles,
            'title': title,
        }

class BlackboardCollaborateUltraIE(InfoExtractor):
    # Support format of either host/webapps/collab-ultra/tool/collabultra\?course_id=course_id or
    #                          host/ultra/courses/course_id/cl/outline
    _VALID_URL = r'''(?x)
                        https://(?P<host>[\w\.]+)/
                        ((webapps/collab-ultra/tool/collabultra\?course_id=(?P<course_id>[\d_]+))
                        |(ultra/courses/(?P<course_id2>[\d_]+)/cl/outline))'''

    _TESTS = [ # All Require a login
        {
            'url': 'https://umb.umassonline.net/webapps/collab-ultra/tool/collabultra?course_id=_70544_1',
            'only_matching': True,
        },
        {
            'url': 'https://online.uwl.ac.uk/webapps/collab-ultra/tool/collabultra?course_id=_1445',
            'only_matching': True,
        },
        {
            'url': 'https://lms.mu.edu.sa/webapps/collab-ultra/tool/collabultra?course_id=_65252_1&mode=cpview',
            'only_matching': True,
        },
        {
            'url': 'https://nestor.rug.nl/webapps/collab-ultra/tool/collabultra?course_id=_404619_1',
            'only_matching': True,
        },
    ]
    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        course_id = mobj.group('course_id') or mobj.group('course_id2')
        host = mobj.group('host')

        webpage = self._download_webpage(
            f'https://{host}/webapps/collab-ultra/tool/collabultra/lti/launch?course_id={course_id}', course_id)

        # Get attribute values from html. These will later be used as POST data for a request.
        attrs = dict(re.findall(r'<input[^>]+name="(?P<name>[^"]+)"[^>]+value="(?P<value>[^"]+)"', webpage))

        # Url to retrieve information about playlist from
        region_url = self._html_search_regex(r'<form[^>]+action="([^"]+)"', webpage, 'form_action')

        # Get authentication token
        webpage = self._request_webpage(region_url, course_id, data=urlencode_postdata(attrs))
        token = urllib.parse.unquote(webpage.url.split('token=')[1])

        # Download playlist information
        playlist_host = region_url.replace('/lti', '')
        playlist_info = self._download_json(f'{playlist_host}/collab/api/csa/recordings', None, headers={'Authorization': f'Bearer {token}'})

        # Write playlist entries and send to BlackboardCollaborateIE
        entries = []
        for i in playlist_info['results']:
            current_url = self.url_result(f'{playlist_host}/collab/ui/session/playback/load/{i["id"]}?authToken={token}', ie=BlackboardCollaborateIE.ie_key(), video_id=i['id'])['url']
            entries.append({
                'id': i['id'],
                '_type': 'url',
                'url': current_url,
                'filesize': i['storageSize'],
                'ie_key': BlackboardCollaborateIE.ie_key(),
                })

        title = playlist_info.get('name')

        return self.playlist_result(entries, title, playlist_count=playlist_info['size'])