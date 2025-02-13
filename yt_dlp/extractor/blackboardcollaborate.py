from .common import InfoExtractor
from ..utils import (
    UnsupportedError,
    int_or_none,
    float_or_none,
    join_nonempty,
    jwt_decode_hs256,
    mimetype2ext,
    parse_iso8601,
    parse_qs,
    url_or_none,
)
from ..utils.traversal import traverse_obj



class BlackboardCollaborateIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        https?://
                        (?P<region>[a-z]+)(?:-lti)?\.bbcollab\.com/
                        (?:
                            collab/ui/session/playback/load|
                            recording
                        )/
                        (?P<id>[^/?#]+)'''
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

    def _call_api(self, region, video_id, path=None, token=None, note=None, fatal=False):
        # Ref: https://github.com/blackboard/BBDN-Collab-Postman-REST
        return self._download_json(
            join_nonempty(f'https://{region}.bbcollab.com/collab/api/csa/recordings', video_id, path, delim='/'),
            video_id, note or 'Downloading JSON metadata', fatal=fatal,
            headers={'Authorization': f'Bearer {token}'} if token else None)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        region = mobj.group('region')
        video_id = mobj.group('id')
        token = parse_qs(url).get('authToken', [None])[-1]

        video_info = self._call_api(region, video_id, path='data/secure', token=token, note='Trying auth token')
        if video_info:
            video_extra = self._call_api(region, video_id, token=token, note='Retrieving extra attributes')
        else:
            video_info = self._call_api(region, video_id, path='data', note='Trying fallback', fatal=True)
            video_extra = {}

        formats = traverse_obj(video_info, ('extStreams', lambda _, v: url_or_none(v['streamUrl']), {
            'url': 'streamUrl',
            'ext': ('contentType', {mimetype2ext}),
            'aspect_ratio': ('aspectRatio', {float_or_none}),
        }))

        if filesize := traverse_obj(video_extra, ('storageSize', {int_or_none})):
            for fmt in formats:
                fmt['filesize'] = filesize

        subtitles = {}
        for subs in traverse_obj(video_info, ('subtitles', lambda _, v: url_or_none(v['url']))):
            subtitles.setdefault(subs.get('lang') or 'und', []).append({
                'name': traverse_obj(subs, ('label', {str})),
                'url': subs['url'],
            })

        for live_chat_url in traverse_obj(video_info, ('chats', ..., 'url', {url_or_none})):
            subtitles.setdefault('live_chat', []).append({'url': live_chat_url})

        return {
            **traverse_obj(video_info, {
                'title': ('name', {str}),
                'timestamp': ('created', {parse_iso8601}),
                'duration': ('duration', {int_or_none(scale=1000)}),
            }),
            'formats': formats,
            'id': video_id,
            'subtitles': subtitles,
        }
