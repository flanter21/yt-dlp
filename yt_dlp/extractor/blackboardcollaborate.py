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
                        (?P<id>[^/]+)'''
    _TESTS = [
        {
            'url': 'https://us-lti.bbcollab.com/collab/ui/session/playback/load/0a633b6a88824deb8c918f470b22b256',
            'md5': 'bb7a055682ee4f25fdb5838cdf014541',
            'info_dict': {
                'id': '0a633b6a88824deb8c918f470b22b256',
                'title': 'HESI A2 Information Session - Thursday, May 6, 2021 - recording_1',
                'ext': 'mp4',
                'duration': 1896000,
                'timestamp': 1620331399,
                'upload_date': '20210506',
            },
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
        mobj = self._match_valid_url(url)
        region = mobj.group('region')
        video_id = mobj.group('id')
        info = self._download_json(
            f'https://{region}.bbcollab.com/collab/api/csa/recordings/{video_id}/data', video_id)
        duration = info.get('duration')
        title = info['name']
        upload_date = info.get('created')
        streams = info['streams']
        formats = [{'format_id': k, 'url': url} for k, url in streams.items()]

        return {
            'duration': duration,
            'formats': formats,
            'id': video_id,
            'timestamp': parse_iso8601(upload_date),
            'title': title,
        }

class BlackboardCollaborateUltraIE(InfoExtractor):
    # Support format of either host/webapps/collab-ultra/tool/collabultra\?course_id=course_id or
    #                          host/ultra/courses/course_id/cl/outline
    _VALID_URL = r'''(?x)
                        https://(?P<host>[\w\.]+)/
                        ((webapps/collab-ultra/tool/collabultra\?course_id=(?P<course_id>[\d_]+))
                        |(ultra/courses/(?P<course_id2>[\d_]+)/cl/outline))'''

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